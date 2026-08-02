import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../themes";
import { OTPInput } from "../OTPInput";

function Wrapper({ onChange }: { onChange: (v: string) => void }) {
  const [value, setValue] = React.useState("");
  return (
    <ThemeProvider>
      <OTPInput length={6} value={value} onChange={v => { setValue(v); onChange(v); }} label="Verification code" />
    </ThemeProvider>
  );
}

describe("OTPInput accessibility and behavior (spec section 16)", () => {
  it("exposes one real, labeled, numeric text field for screen readers", () => {
    render(<Wrapper onChange={() => {}} />);
    const input = screen.getByLabelText("Verification code");
    expect(input.props.keyboardType).toBe("number-pad");
    expect(input.props.accessibilityHint).toMatch(/6-digit/);
  });

  it("strips non-digit characters and truncates to the configured length (paste support)", () => {
    const onChange = jest.fn();
    render(<Wrapper onChange={onChange} />);
    fireEvent.changeText(screen.getByLabelText("Verification code"), "12a34-5678");
    expect(onChange).toHaveBeenCalledWith("123456");
  });

  it("supports iOS/Android autofill via textContentType/autoComplete", () => {
    render(<Wrapper onChange={() => {}} />);
    const input = screen.getByLabelText("Verification code");
    expect(input.props.textContentType).toBe("oneTimeCode");
    expect(input.props.autoComplete).toBe("sms-otp");
  });
});
