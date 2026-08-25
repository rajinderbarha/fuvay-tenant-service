import React from "react";
import Svg, { Path } from "react-native-svg";

export interface FuvayIconProps {
  size?: number;
  accessibilityLabel?: string;
}

/**
 * Official Fuvay symbol from assets/fuvay-icon.svg.
 *
 * Keeping the paths in a native SVG component preserves sharp edges at every
 * density and avoids shipping a second raster interpretation of the mark.
 */
export function FuvayIcon({ size = 32, accessibilityLabel = "Fuvay" }: FuvayIconProps) {
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 228 217"
      fill="none"
      accessibilityRole="image"
      accessibilityLabel={accessibilityLabel}
    >
      <Path d="M130.05 43.6744H157.98V22.6932C157.98 10.1549 147.825 0 135.286 0H92.0149C79.6444 0 69.5566 9.90311 69.3216 22.2736L67.811 104.856C90.0678 101.532 107.591 87.8524 108.766 62.1714C109.454 47.3503 118.736 43.6744 130.05 43.6744Z" fill="#0563FE" />
      <Path d="M95.758 172.6H67.8279V193.581C67.8279 206.12 77.9828 216.274 90.5211 216.274H133.793C146.163 216.274 156.251 206.371 156.486 194.001L157.997 111.419C135.74 114.742 118.216 128.422 117.041 154.103C116.353 168.924 107.071 172.6 95.758 172.6Z" fill="#0563FE" />
      <Path d="M39.4278 120.532V103.529H59.4187V62.2383H27.9133C12.5048 62.2551 0 74.7431 0 90.1684V136.612C0 151.652 12.1859 163.838 27.2252 163.838H108.414C108.414 139.852 88.9434 120.415 64.9577 120.465L39.4278 120.516V120.532Z" fill="#02154A" />
      <Path d="M188.142 95.7417V112.745H168.152V154.036H199.657C215.082 154.036 227.587 141.531 227.587 126.106V79.6617C227.587 64.6224 215.401 52.4365 200.362 52.4365H119.173C119.173 76.4222 138.644 95.8592 162.629 95.8088L188.159 95.7584L188.142 95.7417Z" fill="#02154A" />
    </Svg>
  );
}
