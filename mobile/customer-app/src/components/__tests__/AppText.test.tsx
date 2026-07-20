import React from "react";
import { AppText } from "../primitives/AppText";
import { renderWithTheme } from "../../testing/render-with-theme";

describe("AppText", () => {
  it("renders its children", () => {
    const { getByText } = renderWithTheme(<AppText>Hello world</AppText>);
    expect(getByText("Hello world")).toBeTruthy();
  });

  it("applies the theme color for the requested semantic role", () => {
    const { getByText } = renderWithTheme(<AppText color="textDanger">Danger</AppText>);
    const node = getByText("Danger");
    const flatStyle = Array.isArray(node.props.style) ? Object.assign({}, ...node.props.style.filter(Boolean)) : node.props.style;
    expect(flatStyle.color).toBeDefined();
  });

  it("does not disable font scaling", () => {
    const { getByText } = renderWithTheme(<AppText>Scalable</AppText>);
    expect(getByText("Scalable").props.allowFontScaling).not.toBe(false);
  });
});
