import { Field, Input, Text } from "@chakra-ui/react";

/**
 * 基本情報セクションコンポーネント
 */
export function BasicInfoSection({
  input,
  question,
  intro,
  isReportIdValid,
  reportIdErrorMessage,
  onIdChange,
  onQuestionChange,
  onIntroChange,
}: {
  input: string;
  question: string;
  intro: string;
  isReportIdValid: boolean;
  reportIdErrorMessage: string;
  onIdChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onQuestionChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onIntroChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <>
      <Field.Root>
        <Field.Label>タイトル</Field.Label>
        <Input
          value={question}
          onChange={onQuestionChange}
          placeholder="例：人類が人工知能を開発・展開する上で、最優先すべき課題は何でしょうか？"
        />
        <Field.HelperText>レポートのタイトルを記載します</Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>調査概要</Field.Label>
        <Input
          value={intro}
          onChange={onIntroChange}
          placeholder="例：このAI生成レポートは、パブリックコメントにおいて寄せられた意見に基づいています。"
        />
        <Field.HelperText>コメントの集計期間や、コメントの収集元など、調査の概要を記載します</Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>ID</Field.Label>
        <Input
          w={"40%"}
          value={input}
          onChange={onIdChange}
          placeholder="例：example"
          aria-invalid={!isReportIdValid}
          borderColor={!isReportIdValid ? "red.300" : undefined}
          _hover={!isReportIdValid ? { borderColor: "red.400" } : undefined}
        />
        {!isReportIdValid && (
          <Text color="red.500" fontSize="sm" mt={1}>
            {reportIdErrorMessage}
          </Text>
        )}
        <Field.HelperText>英字小文字と数字とハイフンのみ(URLで利用されます)</Field.HelperText>
      </Field.Root>
    </>
  );
}
