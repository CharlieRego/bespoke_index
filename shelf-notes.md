# Shelf notes

Working notes from this project — tracked in git.

---

## `.env` format: spaces and quotes

`.env` files are plain text. Different tools parse them with slightly different rules. Spaces and quotes change **what string actually gets stored** as the secret.

### What you want stored

API keys should be stored as the raw key characters only — no spaces, no quote marks.

### Preferred form

```env
AA_MAIN_PROJ_KEY=aa_abc123
```

Most loaders set name `AA_MAIN_PROJ_KEY` → value `aa_abc123`. That is what `-H "x-api-key: ..."` should send.

### Spaces around `=`

```env
AA_MAIN_PROJ_KEY = aa_abc123
```

Some parsers trim; others keep a leading space on the value, or treat the variable name as `AA_MAIN_PROJ_KEY ` (trailing space). Then `getenv("AA_MAIN_PROJ_KEY")` may miss it, or the sent key includes a space → `Invalid API key`.

### Quotes

```env
AA_MAIN_PROJ_KEY="aa_abc123"
```

Quote-aware loaders (many Python dotenv setups) strip quotes. Naive / shell-style loaders keep them, so the header becomes `x-api-key: "aa_abc123"` including the `"` characters → API rejects it. Same risk with single quotes.

### Spaces + quotes together

```env
AA_MAIN_PROJ_KEY = "aa_abc123"
```

A picky parser may combine all of the above. The key “is in `.env`,” but the string that reaches `curl` or the app is not exactly the issued secret.

### `curl` / CMD do not load `.env`

`.env` is only read by programs that explicitly load it (dotenv, frameworks, etc.). Shell/`curl` send whatever literal string you put in the header. Passing `-H "x-api-key: AA_MAIN_PROJ_KEY"` sends the **variable name**, not the value.

### Rule of thumb

```env
NAME=value
```

- no spaces around `=`
- no quotes unless the loader needs them for values that contain spaces
- no trailing spaces on the line
- one secret per line

For API keys (no spaces in the value), unquoted `KEY=value` is the safest portable form. APIs check exact string equality — one extra space or `"` is enough to fail.
