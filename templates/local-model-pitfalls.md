## Local model pitfalls (seen in past PRs; check your output against these)
- Imports: use only paths that exist (see the code map). If a task lists import lines, copy them exactly.
- A failing test may be wrong. If the implementation matches the spec and the test does not, say so in your notes
  and fix the test (when it is yours to edit); never bend working code to match a bad expectation.
- `as const` only goes on literals (`[...] as const`, `{...} as const`), never on a `.map(...)` or other call.
- `as const` arrays are readonly: type them `readonly T[]` instead of casting.
- Config values declared `as const` are literal types: `let debt = CONFIG.startDebt` is typed `5500`. Annotate: `let debt: number`.
- Literal unions widen inside object literals: `{ ...x, outcome: "down" }` assigned to a `const` becomes `string`.
  Type the variable (`const next: State = ...`) or build it through a typed helper.
- No `any`, in code or tests; type fakes against the real interfaces. Import every symbol you use.
- React lint: no `setState` inside `useEffect`, no reading/writing `ref.current` during render. Do side effects in
  the event handler that causes them. JSX text with `'` needs `&apos;`.
- Text that tests match as one string (headers, summary lines) must be one template literal, not `{a} text {b}`.
- Test fixtures: build them in one step (`const base = make(); const s = { ...base, x: 1 }`), never reference a
  variable inside its own initializer; use real data from the project's data modules.
- No-op checks compare against the exact object passed in (`const input = {...}; expect(f(input)).toBe(input)`).
- "Creative" strings (ASCII art, copy): check that they actually say what the spec asks for.
