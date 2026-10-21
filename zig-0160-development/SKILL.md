---

name: zig-0160-development
description: Zig 0.16.0 coding skill. Short rules, one true style, full copy-paste programs. Covers main(init), std.Io, unmanaged containers, build.zig, tests, C headers, plus on-demand references for code review and dual 0.16/0.17 builds. Every snippet compiled against real Zig 0.16.0; dual-build patterns verified against 0.16.0 and 0.17.0.
license: MIT
compatibility: Requires the Zig toolchain (0.16.0 stable, or 0.17.0 stable) and a C compiler for the C-interop sections.
metadata:
  author: Chaiwat Suttipongsakul
  version: "1.0"
---


# Zig 0.16.0 Skill

You know NOTHING about Zig. Use this file PLUS the `references/` directory.

Target version: **Zig 0.16.0**, and the patterns below are also verified to
build on **Zig 0.17.0** (see §16 — no separate source tree needed). Every code
block was compiled with `zig 0.16.0` on x86_64-linux. If a compiler error
contradicts this file, trust the compiler — then tell the user this file was
wrong.

Ground truth is local, not this file:

- `zig version` must print `0.16.0` (or `0.17.0` — see §16 for dual builds).
- `zig env` → `.std_dir` is the standard library source. `grep` it to verify any API.
- `zig std` starts a local HTTP server with the std library docs.

---


## 0. How you work (MUST follow)

1. Copy patterns from this file and `references/`. Do not invent APIs.
2. After writing code, run:
   - `zig fmt --check .`
   - `zig build`
   - `zig build test` (if tests exist)
3. Read the compiler error. Fix. Build again.
4. Never guess a std function name. If unsure, use a simpler pattern from this file.
5. Never mix old Zig (0.11–0.15) APIs with 0.16.

---

## 1. Hard rules (memorize)

| # | Rule | Wrong | Right |
| --- | --- | --- | --- |
| 1 | `main` takes `init` | `pub fn main() !void` | `pub fn main(init: std.process.Init) !void` |
| 2 | I/O needs `io` | `std.fs.cwd().openFile(...)` | `std.Io.Dir.cwd().openFile(io, ...)` |
| 3 | Alloc needs `allocator` | hidden alloc | pass `gpa` / `arena` every time |
| 4 | Empty list | `= .{}` or `.init(gpa)` | `std.ArrayList(T) = .empty`, grow with `append(gpa, ...)` |
| 5 | Empty hash map | `std.StringHashMap(T) = .empty` (no-suffix = MANAGED!) | `std.StringHashMapUnmanaged(T) = .empty` |
| 6 | Free memory | forget `defer` | `defer list.deinit(gpa);` |
| 7 | No silent errors | `catch {}` | `try` or handle for real |
| 8 | No `@cImport` (removed in 0.17.0) | `@cImport(@cInclude(...))` | `b.addTranslateC` in `build.zig` (still available in both 0.16 and 0.17) |
| 9 | Strings | C-style `char*` thinking | `[]const u8` (bytes + length) |
| 10 | Format strings | `"{}"` for string | `"{s}"` string, `"{d}"` int, `"{t}"` error/enum, `"{f}"` custom `format()` method |
| 11 | End every statement | missing `;` | always `;` |
| 12 | Heap struct init | field-by-field after `create` | `p.* = .{ ... }` full struct literal |
| 13 | Safe casts on input | unchecked `@intCast(x)` | bounds check; enum tags via `std.enums.fromInt` |
| 14 | Safe buffer print | `bufPrint(...) catch unreachable` | `try bufPrint(...)` or `allocPrint` |
| 15 | Realloc under defer | `free(buf); buf = alloc(...)` | `realloc` or alloc new before free |
| 16 | Slices & C strings | pass `[]u8` to C `char*` | `gpa.dupeZ(u8, s)` (need null terminator) |
| 17 | CLI args | `std.process.argsAlloc` (removed in 0.16) | `init.minimal.args.toSlice(arena)` → `[]const [:0]const u8`; or `Args.Iterator` for zero-alloc |
| 18 | Print JSON | `"{}"` with `std.json.fmt(...)` (prints a struct dump!) | `"{f}"` |
| 19 | Custom `format()` method | `{}` (ignores it) | `{f}`; signature `format(self: T, w: *std.Io.Writer) std.Io.Writer.Error!void` |

---

## 2. One true `main` (ALWAYS use this)

```zig
const std = @import("std");

pub fn main(init: std.process.Init) !void {
    const gpa = init.gpa; // heap allocator
    const io = init.io; // I/O handle (files, sleep, net, ...)
    const arena = init.arena.allocator(); // free-all-at-exit allocator

    // args: iterate, no allocation needed
    var it = std.process.Args.Iterator.init(init.minimal.args);
    while (it.next()) |arg| {
        std.debug.print("arg={s}\n", .{arg});
    }

    // env
    if (init.environ_map.get("HOME")) |home| {
        std.debug.print("HOME={s}\n", .{home});
    }

    _ = gpa;
    _ = io;
}
```

What each thing is:

- `gpa` → temporary heap memory (lists, maps, buffers you free)
- `arena` → short-lived stuff for whole process
- `io` → MUST pass into every file/net/sleep call
- `init.environ_map` → `*std.process.Environ.Map`; `.get("KEY")` returns `?[]const u8`
- `init.preopens` → WASI preopened dirs (void on normal OSes, zero cost)
- Alternative: `main(init: std.process.Init.Minimal)` for only raw args+env,
or plain `main()` for no args/env at all.

Library functions that do I/O or alloc must take parameters:

```zig
fn doWork(io: std.Io, gpa: std.mem.Allocator, path: []const u8) !void {
    _ = io;
    _ = gpa;
    _ = path;
}
```

---

## 12. Idioms worth copying

### Pass capabilities (DI)

```zig
fn save(
    io: std.Io,
    gpa: std.mem.Allocator,
    path: []const u8,
    bytes: []const u8,
) !void {
    try std.Io.Dir.cwd().writeFile(io, .{
        .sub_path = path,
        .data = bytes,
    });
    _ = gpa;
}
```

### Scratch arena in a loop

```zig
fn handleMany(gpa: std.mem.Allocator) !void {
    var arena_inst = std.heap.ArenaAllocator.init(gpa);
    defer arena_inst.deinit();
    const arena = arena_inst.allocator();

    var i: usize = 0;
    while (i < 10) : (i += 1) {
        defer _ = arena_inst.reset(.retain_capacity);
        const tmp = try arena.alloc(u8, 64);
        _ = tmp;
    }
}
```

### I/O root when you have no `init` (libraries, tests)

```zig
// Last resort: a single-threaded Io you own (prefer threading io through).
var threaded: std.Io.Threaded = .init_single_threaded;
const io = threaded.io();
```

---

## 15. Reviewing Zig code (bug hunting)

When asked to review Zig code, FIRST read `references/review-catalog.md` and follow its procedure:

1. Compile it first (`zig build`, or `zig build-exe file.zig`). Fix compile errors before hunting logic bugs.
2. Run the tests: `zig build test`. Leaks fail the run — the test allocator is your best bug finder.
3. Walk the bug catalog in that file. For each hit report: file:line, severity (critical / major / minor), what's wrong, and the fix.
4. Do not invent bugs. Only report ones you can point to.

*Full catalog lives in `references/review-catalog.md`.*


## 16. Coding for both Zig 0.16.0 and 0.17.0

Default: write the §§1–§14 forms — they build on 0.17 too. You only need `references/dual-016-017.md` when the task mentions 0.17, or when 0.16 source fails on the 0.17 toolchain. FIRST read that file, then follow it.

Dual-safe core (stable on both, no version branches needed): `main(init: std.process.Init)`, `std.Io.*`, unmanaged `.empty` containers, `std.enums.fromInt`, `std.heap.DebugAllocator`, `b.addTranslateC`, `std.fmt.bufPrintSentinel`, `std.meta.fieldNames`. Hard rule: no `@cImport`, no `bufPrintZ`, no `dupeZ`, no `**`, no `void{}`, no `i0`.

*Full dual-build reference lives in `references/dual-016-017.md`.*


## References (load on demand)

Progressive disclosure: the files below hold the long-form material. Load only what the task needs.

- `references/language-basics.md` — §3 language basics (values, pointers, control flow, structs, errors, comptime, tests, casting, allocators).
- `references/containers-and-io.md` — §4 containers (ArrayList, hash maps, priority queue) + §5 I/O (`std.Io`, files, sleep, stdout, subprocess, JSON, mutex, random, net, concurrency, logging).
- `references/build-and-templates.md` — §6 full program templates + §7 build system (build.zig, zon, deps, translate-c, cross-compile, test flags).
- `references/migration-errors-builtins.md` — §8 old→0.16 migration table, §9 compiler errors→fix, §10 type-creating builtins, §11 packed structs/bitcast, §13 final checklist, §14 extra commands.
- `references/review-catalog.md` — §15 bug-hunting catalog for code review.
- `references/dual-016-017.md` — §16 dual-build (0.16 + 0.17) guide.

