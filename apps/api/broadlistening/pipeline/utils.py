import json
import os
import traceback
from datetime import datetime, timedelta

with open("./specs.json") as f:
    specs = json.load(f)


def typed_message(t, m):
    if t == "system":
        return {"role": "system", "content": m}
    if t == "human":
        return {"role": "user", "content": m}
    if t == "ai":
        return {"role": "assistant", "content": m}
    raise Exception("Unknown message type in prompt: " + t)


def messages(prompt, input):
    lines = prompt.strip().splitlines()
    results = []
    t = None
    m = ""
    for line in lines:
        if line.startswith("/"):
            if t is not None:
                results.append((t, m))
            t = line[1:].strip()
            m = ""
        else:
            m += line + "\n"
    results.append((t, m))
    results.append(("human", input))
    return [typed_message(t, m) for (t, m) in results]


def validate_config(config):
    if "input" not in config:
        raise Exception("Missing required field 'input' in config")
    if "question" not in config:
        raise Exception("Missing required field 'question' in config")
    valid_fields = ["input", "question", "model", "name", "intro"]
    step_names = [x["step"] for x in specs]
    for key in config:
        if key not in valid_fields and key not in step_names:
            raise Exception(f"Unknown field '{key}' in config")
    for step_spec in specs:
        valid_options = list(step_spec.get("options", {}).keys())
        if step_spec.get("use_llm"):
            valid_options = valid_options + ["prompt", "model", "prompt_file"]
        for key in config.get(step_spec["step"], {}):
            if key not in valid_options:
                raise Exception(f"Unknown option '{key}' for step '{step_spec['step']}' in config")


def decide_what_to_run(config, previous):
    # find last previously tracked jobs (digging in case previous run failed)
    previous_jobs = []
    _previous = config.get("previous", None)
    while _previous and _previous.get("previous", None) is not None:
        _previous = _previous["previous"]
    if _previous:
        previous_jobs = _previous.get("completed_jobs", []) + _previous.get("previously_completed_jobs", [])

    # utility function to check if params changed

    def different_params(step):
        keys = step["dependencies"]["params"]
        if step.get("use_llm", False):
            # automagically track prompt and model for llm jobs
            keys += ["prompt", "model"]
        match = [x for x in previous_jobs if x["step"] == step["step"]]
        prev = match[0]["params"]
        next = config[step["step"]]
        diff = [key for key in keys if prev.get(key, None) != next.get(key, None)]
        for key in diff:
            print(f"(!) {step} step parameter '{key}' changed from '{prev.get(key)}' to '{next.get(key)}'")
        return diff

    # figure out which steps need to run and why
    plan = []
    for step in specs:
        stepname = step["step"]
        run = True
        reason = None
        found_prev = len([x for x in previous_jobs if x["step"] == step["step"]]) > 0
        if config.get("force", False):
            reason = "forced with -f"
        elif config.get("only", None) is not None and config["only"] != stepname:
            run = False
            reason = "forced another step with -o"
        elif config.get("only") == stepname:
            reason = "forced this step with -o"
        elif not found_prev:
            reason = "not trace of previous run"
        elif not os.path.exists(f"outputs/{config['output_dir']}/{step['filename']}"):
            reason = "previous data not found"
        else:
            deps = step["dependencies"]["steps"]
            changing_deps = [x["step"] for x in plan if (x["step"] in deps and x["run"])]
            if len(changing_deps) > 0:
                reason = "some dependent steps will re-run: " + (", ".join(changing_deps))
            else:
                diff_params = different_params(step)
                if len(diff_params) > 0:
                    print("diff_params", diff_params)
                    reason = "some parameters changed: " + ", ".join(diff_params)
                else:
                    run = False
                    reason = "nothing changed"
        plan.append({"step": stepname, "run": run, "reason": reason})
    return plan


def initialization(sysargv):
    job_file = sysargv[1]
    job_name = os.path.basename(job_file).split(".")[0]

    with open(job_file) as f:
        config = json.load(f)

    validate_config(config)
    config["output_dir"] = job_name

    for i, option in enumerate(sysargv):
        if option == "-f":
            config["force"] = True
        if option == "-o":
            config["only"] = sysargv[i + 1]
        if option == "--skip-interaction":
            config["skip-interaction"] = True

    output_dir = config["output_dir"]

    # check if job has run before
    previous = False
    if os.path.exists(f"outputs/{output_dir}/status.json"):
        with open(f"outputs/{output_dir}/status.json") as f:
            previous = json.load(f)
        config["previous"] = previous

    # crash if job is already running and locked
    if previous and previous["status"] == "running":
        if datetime.fromisoformat(previous["lock_until"]) > datetime.now():
            print("Job already running and locked. Try again in 5 minutes.")
            raise Exception("Job already running.")
        else:
            print("Hum, the last Job crashed a while ago...Proceeding!")

    # set default LLM model
    if "model" not in config:
        config["model"] = "gpt-3.5-turbo"

    # prepare configs for each jobs
    for step_spec in specs:
        step = step_spec["step"]
        if step not in config:
            config[step] = {}
        # set default option values
        if "options" in step_spec:
            for key, value in step_spec["options"].items():
                if key not in config[step]:
                    config[step][key] = value
        # try and include source code
        try:
            with open(f"steps/{step}.py") as f:
                config[step]["source_code"] = f.read()
        except Exception:
            print(f"Warning: could not find source code for step '{step}'")
        # resolve common options for llm-based jobs
        if step_spec.get("use_llm", False):
            # resolve prompt
            if "prompt" not in config.get(step):
                file = config.get(step).get("prompt_file", "default")
                with open(f"prompts/{step}/{file}.txt") as f:
                    config[step]["prompt"] = f.read()
            # resolve model
            if "model" not in config.get(step):
                if "model" in config:
                    config[step]["model"] = config["model"]

    # create output directory if needed
    if not os.path.exists(f"outputs/{output_dir}"):
        os.makedirs(f"outputs/{output_dir}")

    # check if user is happy with the plan...
    plan = decide_what_to_run(config, previous)
    if "skip-interaction" not in config:
        print("So, here is what I am planning to run:")
        for step in plan:
            print(step)
        print("Looks good? Press enter to continue or Ctrl+C to abort.")
        input()

    # ready to start!
    update_status(
        config,
        {
            "plan": plan,
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "completed_jobs": [],
        },
    )
    return config


# (!) make sure to always use this function to update status...
def update_status(config, updates):
    output_dir = config["output_dir"]
    for key, value in updates.items():
        if value is None and key in config:
            del config[key]
        else:
            config[key] = value
    config["lock_until"] = (datetime.now() + timedelta(minutes=5)).isoformat()
    with open(f"outputs/{output_dir}/status.json", "w") as file:
        json.dump(config, file, indent=2)


def update_progress(config, incr=None, total=None):
    if total is not None:
        update_status(config, {"current_job_progress": 0, "current_jop_tasks": total})
    elif incr is not None:
        update_status(config, {"current_job_progress": config["current_job_progress"] + incr})


def run_step(step, func, config):
    # check the plan before running...
    plan = [x for x in config["plan"] if x["step"] == step][0]
    if not plan["run"]:
        print(f"Skipping '{step}'")
        return
    # update status before running...
    update_status(
        config,
        {
            "current_job": step,
            "current_job_started": datetime.now().isoformat(),
        },
    )
    print("Running step:", step)
    # run the step...
    func(config)
    # update status after running...
    update_status(
        config,
        {
            "current_job_progress": None,
            "current_jop_tasks": None,
            "completed_jobs": config.get("completed_jobs", [])
            + [
                {
                    "step": step,
                    "completed": datetime.now().isoformat(),
                    "duration": (
                        datetime.fromisoformat(datetime.now().isoformat())
                        - datetime.fromisoformat(config["current_job_started"])
                    ).total_seconds(),
                    "params": config[step],
                }
            ],
        },
    )


def termination(config, error=None):
    if "previous" in config:
        # remember all previously completed jobs
        old_jobs = config["previous"].get("completed_jobs", []) + config["previous"].get(
            "previously_completed_jobs", []
        )
        newly_completed = [j["step"] for j in config.get("completed_jobs", [])]
        config["previously_completed_jobs"] = [o for o in old_jobs if o["step"] not in newly_completed]
        # now we can drop previous key (we don't want to store infinite history)
        del config["previous"]
    if error is None:
        update_status(
            config,
            {
                "status": "completed",
                "end_time": datetime.now().isoformat(),
            },
        )
        print("Pipeline completed.")
    else:
        update_status(
            config,
            {
                "status": "error",
                "end_time": datetime.now().isoformat(),
                "error": f"{type(error).__name__}: {error}",
                "error_stack_trace": traceback.format_exc(),
            },
        )
        raise error
