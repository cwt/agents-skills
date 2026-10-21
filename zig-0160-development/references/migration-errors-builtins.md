# Migration, errors, builtins, packed structs, checklist, commands (Zig 0.16.0)

Companion reference. Load on demand.

## 8. OLD Zig → 0.16 (migration table)

| Old (do not use) | New (0.16) |
| --- | --- |
| `pub fn main() !void` | `pub fn main(init: std.process.Init) !void` |
| `var gpa = std.heap.GeneralPurposeAllocator(.{}){};` in main | `const gpa = init.gpa;` |
| `std.heap.page_allocator` everywhere in apps | prefer `init.gpa` / `init.arena` |
| `std.heap.GeneralPurposeAllocator` / `ThreadSafeAllocator` | `std.heap.DebugAllocator(.{})` with `= .init` (thread-safe) |
| `std.process.argsAlloc` / `getArgsAlloc` | `std.process.Args.Iterator.init(init.minimal.args)` + `.next()` |
| `std.process.getEnvVarOwned` | `init.environ_map.get("KEY")` |
| `std.process.getCwd(buf)` | `std.process.currentPath(io, buf)` |
| `std.fs.cwd().openFile(path, .{})` | `std.Io.Dir.cwd().openFile(io, path, .{})` |
| `std.fs.cwd().readFileAlloc(allocator, path, max)` | `std.Io.Dir.cwd().readFileAlloc(io, path, gpa, .limited(max))` (error is `StreamTooLong`) |
| `Dir.makeDir` | `Dir.createDir` |
| `Dir.makePath` | `Dir.createDirPath` |
| `Dir.atomicFile` | `Dir.createFileAtomic` |
| `file.close()` | `file.close(io)` |
| `std.time.sleep(ns)` | `try std.Io.sleep(io, .fromNanoseconds(ns), .awake)` |
| `std.time.milliTimestamp()` | `std.Io.Timestamp.now(io, .awake)` (clocks: `.real` `.awake` `.boot`) |
| `std.net.*` | `std.Io.net.*` via `io` (connect needs `.mode = .stream`) |
| `std.crypto.random` | `io.random(&buf)` / `try io.randomSecure(&buf)` |
| `std.Thread.Mutex` | `std.Io.Mutex` (`try mutex.lock(io)`) |
| `std.Thread.Pool` | `std.Io.async` / `std.Io.Group` / `Future(T)` |
| `std.once` | REMOVED — hand-roll it |
| `var list = std.ArrayList(T).init(allocator)` | `var list: std.ArrayList(T) = .empty;` |
| `var map = std.StringHashMap(T).init(gpa)` (managed) | `var map: std.StringHashMapUnmanaged(T) = .empty;` |
| `std.AutoArrayHashMap(K,V)` | `std.array_hash_map.Auto(K,V)` |
| `std.PriorityQueue` `add` / `remove` | `push` / `pop`; init with `.empty` |
| `@cImport({ @cInclude("x.h"); })` | `b.addTranslateC` + `@import("c")` (removed in 0.17.0; `addTranslateC` still available in both) |
| `std.mem.indexOf(u8, hay, needle)` | `std.mem.find(u8, hay, needle)` — note: `indexOf` is a **live alias for `find` in BOTH 0.16 and 0.17** (mem.zig: `pub const indexOf = find;`), so either name compiles; `find` is the canonical spelling |
| `std.mem.trimLeft` | `std.mem.trimStart` |
| `catch {}` / `catch \|_\| {}` | `try` or real handling |
| `std.posix.exit` | `std.process.exit` |
| `std.process.Child.init(...)` | `std.process.spawn(io, .{.argv = ...})` |
| `std.process.Child.run(alloc, io, ...)` | `std.process.run(gpa, io, .{.argv = ...})` |
| `std.fmt.bufPrintZ` | **removed in 0.17.0** — use `std.fmt.bufPrintSentinel(buf, fmt, args, 0)` (identical signature, present in both 0.16 and 0.17) |
| `std.meta.intToEnum(E, v)` | `std.enums.fromInt(E, v) orelse ...` (returns `?E`) |
| `@Type(.{ .int = ... })` | `@Int(.unsigned, 10)` and friends (see §10) |

---


## 9. Compiler errors → fix

| Error text | Fix |
| --- | --- |
| `missing struct field: items` | use `= .empty` not `= .{}` |
| `struct '...' has no member named 'empty'` | you used a MANAGED type: `StringHashMap` (no suffix) is managed — use `StringHashMapUnmanaged` or `.init(gpa)` |
| `root source file struct 'xxx' has no member named 'main'` | export `pub fn main(init: std.process.Init) !void` |
| `unknown identifier: std.net` | use `std.Io.net` and pass `io` |
| `root source file struct 'std' has no member named 'io'` | `std.io` is removed; use `std.Io` |
| `root source file struct 'json' has no member named 'stringify'` | use `std.json.fmt(value, .{})` with `{f}` |
| `root source file struct 'Thread' has no member named 'Mutex'` | use `std.Io.Mutex`: `var mutex: std.Io.Mutex = .init; try mutex.lock(io);` |
| `no field or member function named 'read' in 'Io.Reader'` | use `try r.take(N)` or `r.allocRemaining(gpa, .limited(N))` |
| `member function expected 2 argument(s), found 1` on `reader`/`writer` | pass io: `file.reader(io, &buf)` |
| `unknown identifier: @cImport` / deprecated | use `addTranslateC` |
| `error: root_module` related in build | pass `.root_module = b.createModule(.{...})` into `addExecutable` |
| `pointless discard` | remove unused `_ = x` if `x` is used |
| `unused local constant` | use it, or `_ = name;` |
| `invalid format string 't' for type '?E'` | `{t}` doesn't work on optionals — unwrap first |
| `vector index must be a comptime-known value` | copy vector to array first: `const arr: [N]T = vec;` |
| `pointer to packed struct field cannot coerce` | copy field to local var, or use `extern struct` |
| `switch prong capture may not be discarded` | remove the capture (or use it) |
| `cannot return address of local variable` | 0.16 forbids `return &local` — heap-allocate, or `return undefined` if intentional |
| fingerprint error in `build.zig.zon` | paste the fingerprint value from the error message |
| test timeout after 1.00s | `zig build test --test-timeout-scale=5.0` |
| `integer does not fit in destination type` | `@intCast` out of range — check bounds first (`if (v > max)`) |
| `float cannot fit into integer type` / NaN/Inf | check `std.math.isFinite(f)` before `@trunc`/`@intFromFloat` |
| `enum tag value not found` | `@enumFromInt` invalid tag — use `std.enums.fromInt(Enum, val)` |
| `has no member named 'intToEnum'` in `std.meta` | it's `std.enums.fromInt` now |
| `use of uninitialized value` | initialize allocated struct with `p.* = .{ ... }` |

Verbose errors:

```sh
zig build --error-style=verbose_clear --multiline-errors
```

---


## 10. Type-creating builtins (`@Type` is GONE)

`@Type(...)` was removed in 0.16. Use the 8 dedicated builtins:

| Old | New |
| --- | --- |
| `@Type(.enum_literal)` | `@EnumLiteral()` |
| `@Type(.{ .int = .{ .signedness = .unsigned, .bits = 10 } })` | `@Int(.unsigned, 10)` |
| `@Type(.{ .pointer = ... })` | `@Pointer(size, attrs, Element, sentinel)` |
| `@Type(.{ .fn = ... })` | `@Fn(param_types, param_attrs, ReturnType, attrs)` |
| `@Type(.{ .tuple = ... })` | `@Tuple(&.{ u32, f64 })` |
| `@Type(.{ .struct = ... })` | `@Struct(layout, backing_int_or_null, names, types, attrs)` |
| `@Type(.{ .union = ... })` | `@Union(layout, tag_type, names, types, attrs)` |
| `@Type(.{ .enum = ... })` | `@Enum(tag_type, exhaustive, names, values)` |

Not reifiable (just write the syntax): floats (`f32`), arrays (`[4]u8`),
opaque (`opaque {}`), optionals (`?T`), error unions (`E!T`).
Error sets CANNOT be reified at all — declare with `error{ ... }`.

---


## 11. Packed structs / bitcast (only when needed)

```zig
// @bitCast only same bit size
const raw: u32 = 0x3F800000;
const f: f32 = @bitCast(raw);

// packed union needs every field to be the SAME bit size as the backing int
const U = packed union(u32) {
    integer: u32,
    floating: f32,
};

// packed unions compare directly with == now
const a: U = .{ .integer = 1 };
const same = (a == U{ .integer = 1 });
_ = same;
```

Packed struct/union rules:

1. No pointer fields (store `usize`, convert with `@intFromPtr` / `@ptrFromInt`)
2. No `@Vector` fields
3. In `extern` contexts (e.g. `export var`), `enum`/`packed struct`/`packed union`
   need an EXPLICIT backing/tag int: `enum(u8) { ... }`
4. Prefer `extern struct` for C layouts

---


## 13. Final checklist (before you stop)

- [ ] `main(init: std.process.Init) !void`
- [ ] Got `gpa`, `io`, `arena` from `init` when needed
- [ ] Args via `std.process.Args.Iterator`, env via `init.environ_map.get`
- [ ] Every I/O call got `io`
- [ ] Every grow/free on list/map got `gpa`
- [ ] Containers started with `.empty`
- [ ] `defer x.deinit(gpa)` for owned containers
- [ ] Hash maps: `...Unmanaged` suffix for the unmanaged style
- [ ] Custom `format()` used with `{f}`, JSON printed with `{f}`
- [ ] No `catch {}`
- [ ] No `@cImport`
- [ ] No `std.fs` ambient I/O for new code (use `std.Io.Dir`)
- [ ] No `std.process.Child.init` (use `std.process.spawn(io, ...)`)
- [ ] No `std.io.fixedBufferStream` (use `std.Io.Writer.fixed` or `std.Io.Reader.fixed`)
- [ ] No `std.json.stringify` (use `std.json.fmt` with `{f}`)
- [ ] No `std.Thread.Mutex` (use `std.Io.Mutex` with `try mutex.lock(io)`)
- [ ] No `std.crypto.random` (use `io.random` / `io.randomSecure`)
- [ ] Initialized heap struct with `p.* = .{ ... }` struct literal
- [ ] No unchecked `@intCast` on external data
- [ ] Used `std.enums.fromInt` for untrusted enum tags
- [ ] No `catch unreachable` on `std.fmt.bufPrint`
- [ ] No pointer held into `list.items` across `append()`
- [ ] No pointer into `list.items` held across foreign calls that can re-enter (e.g. Python callbacks)
- [ ] No unconditional `defer cleanup` in async callbacks that can re-queue in-flight work (use latch)
- [ ] Buffer growth under `defer free` uses `realloc` or temp alloc (no double-free)
- [ ] C string calls get null-terminated `[:0]u8` (allocated `len + 1`)
- [ ] Stole reference in C API only with `py_newref` if scope has active `defer py_decref`
- [ ] `zig fmt --check .` ok
- [ ] `zig build` ok
- [ ] `zig build test` ok (if tests)
- [ ] No invented `std` APIs — only patterns from this file; no Zig 0.11–0.15 blog code as truth
- [ ] Read each compiler error, fix it, rebuild before moving on
- [ ] Small clear functions; library code takes `io` + `gpa` parameters
- [ ] Ran the §15 review pass on code you didn't write

---


## 14. Extra commands (basics in §7.1)

```sh
zig build test --test-timeout 500ms  # per-test timeout (default 1s; also --test-timeout-scale=5)
zig build test --fuzz                # fuzz tests using std.testing.fuzz
zig fmt .                            # format in place (vs --check)
zig ast-check src/main.zig           # parse check without building
zig std                              # local std docs HTTP server
```

---

