import { RadioCard } from "@chakra-ui/react";
import * as React from "react";
import { Tooltip } from "./tooltip";

interface RadioCardItemProps extends RadioCard.ItemProps {
  icon?: React.ReactElement;
  label?: React.ReactNode;
  description?: React.ReactNode;
  addon?: React.ReactNode;
  indicator?: React.ReactNode | null;
  indicatorPlacement?: "start" | "end" | "inside";
  inputProps?: React.InputHTMLAttributes<HTMLInputElement>;
  disabled?: boolean;
  disabledReason?: React.ReactNode;
}

export const RadioCardItem = React.forwardRef<HTMLInputElement, RadioCardItemProps>(function RadioCardItem(props, ref) {
  const {
    inputProps,
    label,
    description,
    addon,
    icon,
    indicator = <RadioCard.ItemIndicator />,
    indicatorPlacement = "end",
    disabled,
    disabledReason,
    ...rest
  } = props;

  const hasContent = label || description || icon;
  const ContentWrapper = indicator ? RadioCard.ItemContent : React.Fragment;

  const cardItem = (
    <RadioCard.Item
      {...rest}
      data-disabled={disabled}
      cursor={disabled ? "not-allowed" : rest.cursor}
      css={
        disabled
          ? {
              opacity: 0.3,
              // pointerEvents: 'none',
            }
          : undefined
      }
    >
      <RadioCard.ItemHiddenInput ref={ref} {...inputProps} />
      <RadioCard.ItemControl>
        {indicatorPlacement === "start" && indicator}
        {hasContent && (
          <ContentWrapper>
            {icon}
            {label && <RadioCard.ItemText>{label}</RadioCard.ItemText>}
            {description && <RadioCard.ItemDescription>{description}</RadioCard.ItemDescription>}
            {indicatorPlacement === "inside" && indicator}
          </ContentWrapper>
        )}
        {indicatorPlacement === "end" && indicator}
      </RadioCard.ItemControl>
      {addon && <RadioCard.ItemAddon>{addon}</RadioCard.ItemAddon>}
    </RadioCard.Item>
  );

  // disabledがtrueかつdisabledReasonが存在する場合はTooltipでラップする
  if (disabled && disabledReason) {
    return (
      <Tooltip content={disabledReason} showArrow>
        {cardItem}
      </Tooltip>
    );
  }

  return cardItem;
});

export const RadioCardRoot = RadioCard.Root;
export const RadioCardLabel = RadioCard.Label;
export const RadioCardItemIndicator = RadioCard.ItemIndicator;
