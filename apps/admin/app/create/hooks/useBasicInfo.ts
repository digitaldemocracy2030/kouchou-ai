import { createUUID } from "@/app/utils/uuid";
import { useState } from "react";
import { validateReportId } from "../utils/validation";

/**
 * 基本情報を管理するカスタムフック
 */
export function useBasicInfo() {
  // 基本情報の状態
  const [input, setInput] = useState<string>(() => createUUID());
  const [question, setQuestion] = useState<string>("");
  const [intro, setIntro] = useState<string>("");
  const [isReportIdValid, setIsReportIdValid] = useState<boolean>(true);
  const [reportIdErrorMessage, setReportIdErrorMessage] = useState<string>("");

  /**
   * ID変更時のハンドラー
   */
  const handleIdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newId = e.target.value;
    setInput(newId);
    const reportIdValidation = validateReportId(newId);
    setIsReportIdValid(reportIdValidation.isValid);
    setReportIdErrorMessage(reportIdValidation.errorMessage || "");
  };

  /**
   * タイトル変更時のハンドラー
   */
  const handleQuestionChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuestion(e.target.value);
  };

  /**
   * 調査概要変更時のハンドラー
   */
  const handleIntroChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setIntro(e.target.value);
  };

  /**
   * 基本情報をリセット
   */
  const resetBasicInfo = () => {
    setInput(createUUID());
    setQuestion("");
    setIntro("");
    setIsReportIdValid(true);
    setReportIdErrorMessage("");
  };

  return {
    input,
    question,
    intro,
    isReportIdValid,
    reportIdErrorMessage,
    handleIdChange,
    handleQuestionChange,
    handleIntroChange,
    resetBasicInfo,
  };
}
