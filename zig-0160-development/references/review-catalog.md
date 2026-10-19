# Review catalog (companion to SKILL.md §15)

When asked to review Zig code, follow this procedure:

1. Compile it first (`zig build`, or `zig build-exe file.zig`). Fix compile
   errors before hunting logic bugs.
2. Run the tests: `zig build test`. Leaks fail the run — the test allocator
   is your best bug finder.
3. Walk the bug catalog below. For each hit report: file:line, severity
   (critical / major / minor), what's wrong, and the fix.
4. Do not invent bugs. Only report ones you can point to.

## Memory bugs

| Smell | Check | Fix |
| --- | --- | --- |
| `free(buf); buf = try alloc(...)` with `defer free(buf)` active | double-free if the alloc fails | `realloc`, or alloc to temp before freeing |
| `try gpa.alloc` with no nearby `defer gpa.free` | leak — who owns it? | add `defer`/`errdefer`, or return ownership clearly |
| resource acquired, then `try` without `errdefer` | leak on the error path | `errdefer` on the IMMEDIATE next line |
| `p.field = x` after `gpa.create(T)` | uninitialized fields | `p.* = .{ ... }` struct literal |
| returning a slice from a loop-local arena | dangling after `arena.reset` | allocate from `gpa`, or return owned memory |
| `toOwnedSlice()` then `aw.written()` also used | use-after-move | pick ONE |
| `gpa.dupeZ(...)` result never freed | leak | `defer gpa.free(...)` |
| `defer _ = dbg.deinit();` | hides the leak report | in tests use `std.testing.allocator`; in apps surface the `Check` result |
| unconditional `defer cleanup(x)` in an async/re-queue loop | UAF on next iteration while SQE/op is in flight | guard with latch: `var requeued = false; defer if (!requeued) cleanup(x);` |
| `parent.deinit()` called before finishing/using `parent.child` | child freed before use (UAF) | `defer parent.deinit()` or extract/incref child before parent cleanup |

## Pointer / slice bugs

| Smell | Check | Fix |
| --- | --- | --- |
| pointer into `list.items[i]` kept across `append` | dangling after realloc | store index, or store `*T` in the list |
| `for (list.items) \|*val\|` across foreign/Python re-entrant calls | re-entrancy appends to list, invalidating slice pointer | iterate by index (`while (i < len)`), hold temp ref, re-check bounds after call |
| slice from `w.buffered()` used after more writes | silently overwritten | finish writing first, or copy |
| `const chunk = try r.take(5)` then `chunk[4]` | `take` returns UP TO N bytes | check `chunk.len` |
| slice escaping the scope that owns its buffer | use-after-free | extend the owner's lifetime |

## Error-handling bugs

| Smell | Check | Fix |
| --- | --- | --- |
| `catch {}` / `catch \|_\| {}` | swallowed failure | `try`, or handle and log |
| `errdefer` placed before a `catch` block returning `void`/value | dead code — `errdefer` only runs on error return | move cleanup directly into the `catch` block |
| `bufPrint(...) catch unreachable` | PANICS on overflow | return an error, or `allocPrint` |
| `switch` over an error set without `else` | misses new variants later | add `else` prong |
| `@intCast(x)` / `@enumFromInt(x)` on untrusted input | panic on bad data | bounds check / `std.enums.fromInt` + `orelse` |
| `child.wait(io)` result ignored | zombie process | always `try child.wait(io)` |
| `try` missing on `future.await(io)` when fn returns `!T` | error silently dropped | `try` it |

## I/O bugs

| Smell | Check | Fix |
| --- | --- | --- |
| writer used, no `flush()` | lost output | `try w.flush()` before close/return |
| `openFile` without `defer file.close(io)` | fd leak | defer immediately |
| `readFileAlloc(..., .limited(huge))` or unbounded | memory DoS on big files | small limit + handle `error.StreamTooLong` |
| `std.debug.print` in a hot loop | slow, unbuffered | buffered `Io.File.Writer` |

## Concurrency bugs

| Smell | Check | Fix |
| --- | --- | --- |
| shared `var` mutated from `io.async` tasks | data race | guard with `std.Io.Mutex` (`try lock(io)`) |
| `io.async` assumed to run concurrently | it may run INLINE | `io.concurrent` when ordering matters (handle `error.ConcurrencyUnavailable`) |
| `future` never awaited/cancelled | leaked task resources | `defer _ = future.cancel(io)` |

## Format / print bugs

| Smell | Check | Fix |
| --- | --- | --- |
| `{}` on `std.json.fmt(...)` or a custom `format()` | prints a struct dump | `{f}` |
| `{t}` on `?Error` / `?Enum` | compile error / wrong output | unwrap first |
| `{s}` on `[]const u16` | garbage | `std.unicode.utf16LeToUtf8` first |

## 0.16 API-misuse bugs

| Smell | Check | Fix |
| --- | --- | --- |
| `std.StringHashMap(T) = .empty` | managed type has no `.empty` | `StringHashMapUnmanaged` |
| `file.reader(&buf)` / `file.writer(&buf)` | missing `io` arg | `file.reader(io, &buf)` |
| `std.io.*`, `std.Thread.Mutex`, `std.json.stringify`, `std.process.Child.init` | all removed in 0.16 | see §8 migration table in SKILL.md |
| `std.process.argsAlloc` | removed in 0.16 | `init.minimal.args.toSlice(arena)` or `std.process.Args.Iterator` |
| `std.meta.intToEnum` | gone | `std.enums.fromInt` |

## C-interop bugs

| Smell | Check | Fix |
| --- | --- | --- |
| `[]const u8` passed to C `char*` | missing NUL terminator | `gpa.dupeZ(u8, s)` |
| C preflight returns `N`, buffer of `N` allocated | NUL written out of bounds | allocate `N + 1` |
| `std.mem.span(ptr)` on nullable C pointer | segfault on null | null-check first |
| reference-stealing C API (`PyErr_SetRaisedException`, `SetItem`) called while `defer py_decref` is active | double-free / dangling pointer on scope exit | pass `py_newref(x)` so both the stealing API and defer own distinct increments |

## Review prompt (paste with the code)

```text
Review this Zig 0.16.0 code for bugs. For each issue give file:line,
severity (critical/major/minor), what's wrong, and the fix.
Check: memory ownership (defer/errdefer, double-free, leaks), list pointer
invalidation, error handling (no catch {}), I/O (flush, close, size limits),
concurrency races, format specifiers ({s}/{d}/{t}/{f}), API names against the
skill, C string termination. Do not invent bugs — only report ones you can
point to in the code.
```
