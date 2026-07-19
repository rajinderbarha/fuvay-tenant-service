# Shape, Elevation & Motion System

## Shape
Radius scale shared with spacing doc (`sm/md/lg/xl/full`). No sharp 0-radius
surfaces in the component library — the smallest is `4px` on skeletons.

## Elevation
Four shadow presets (`--shadow-sm/md/lg/overlay`), tuned separately per
theme: light uses low-opacity black shadows; dark uses deeper, more opaque
black shadows (transparent shadows read as invisible on dark surfaces
otherwise). `overlay` is reserved for Modal/Drawer against the page.

## Motion
Durations: `fast 150ms / base 220ms / slow 320ms`, single easing
`cubic-bezier(0.2,0,0,1)` ("standard") for most transitions, with
decelerate/accelerate variants available for entrance/exit-specific motion.
Used for: button hover/active, focus-ring appearance, modal/drawer
transitions, skeleton pulse, spinner rotation.

### Reduced motion
`tokens/motion.ts` exports `motionDuration(ms)` which returns `0` when
`window.matchMedia('(prefers-reduced-motion: reduce)').matches`, for any
component driving animation via JS (e.g. a future toast auto-slide). At the
CSS layer, `theme.css` includes a global
`@media (prefers-reduced-motion: reduce)` block that zeroes all
`animation-duration`/`transition-duration` and disables smooth scrolling,
so even components that didn't explicitly check the media query are safe.
