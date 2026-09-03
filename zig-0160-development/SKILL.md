---
name: zig-0160-development
description: Zig 0.16.0 coding skill for small local LLMs (9B-27B). Short rules, one true style, full copy-paste programs. Covers main(init), std.Io, unmanaged containers, build.zig, tests, C headers.
---

# Zig 0.16.0 Skill (for small local LLMs)

You know NOTHING about Zig. Use ONLY this file.

Target version: **Zig 0.16.0** only.

---

## 0. How you work (MUST follow)

1. Copy patterns from this file. Do not invent APIs.
2. After writing code, run:
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
| 4 | Empty list/map | `= .{}` or `.init(allocator)` | `= .empty` then pass allocator on methods |
| 5 | Free memory | forget `defer` | `defer list.deinit(gpa);` |
| 6 | No silent errors | `catch {}` | `try` or handle for real |
| 7 | No `@cImport` | `@cImport(@cInclude(...))` | `b.addTranslateC` in `build.zig` |
| 8 | Strings | C-style `char*` thinking | `[]const u8` (bytes + length) |
| 9 | Print strings | `"{}"` for string | `"{s}"` for string, `"{d}"` for int, `"{t}"` for error/enum |
| 10 | End every statement | missing `;` | always `;` |
| 11 | Heap struct init | field-by-field after `create` | `p.* = .{ ... }` full struct literal |
| 12 | Safe casts on input | unchecked `@intCast(x)` | bounds check or `std.meta.intToEnum` |
| 13 | Safe buffer print | `bufPrint(...) catch unreachable` | `try bufPrint(...)` or `allocPrint` |
| 14 | Realloc under defer | `free(buf); buf = alloc(...)` | `realloc` or alloc new before free |
| 15 | Slices & C strings | pass `[]u8` to C `char*` | `gpa.dupeZ(u8, s)` (need null terminator) |

---

## 2. One true `main` (ALWAYS use this)

```zig
const std = @import("std");

pub fn main(init: std.process.Init) !void {
    const gpa = init.gpa; // general purpose allocator (heap)
    const io = init.io; // I/O handle (files, sleep, net, ...)
    const arena = init.arena.allocator(); // free-all-at-exit allocator

    // args
    const args = try init.minimal.args.toSlice(arena);
    for (args) |arg| {
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
- `arena` → short-lived stuff for whole process (args ok here)
- `io` → MUST pass into every file/net/sleep call
- `init.environ_map` → environment variables

Library functions that do I/O or alloc must take parameters:

```zig
fn doWork(io: std.Io, gpa: std.mem.Allocator, path: []const u8) !void {
    _ = io;
    _ = gpa;
    _ = path;
}
```

---

## 3. Language basics (short)

### 3.1 Values

```zig
const x: i32 = 42; // cannot change
var y: i32 = 1; // can change
y += 1;

// common types: i32 u32 i64 u64 usize bool f32 f64
// bool is true / false
```

### 3.2 Pointers and optionals

```zig
var n: i32 = 10;
const p: *i32 = &n; // pointer to mutable i32
p.* += 1; // n is now 11

const cp: *const i32 = &n; // pointer to const
_ = cp.*;

// optional: value OR null
var name: ?[]const u8 = null;
name = "zig";
if (name) |n2| {
    std.debug.print("{s}\n", .{n2});
}
const maybe_num: ?i32 = 42;
const v: i32 = maybe_num orelse 0;
_ = v;
```

### 3.3 Arrays, slices, strings

```zig
const arr = [_]i32{ 1, 2, 3, 4 }; // array, length known at compile time
const s: []const i32 = arr[1..3]; // slice = pointer + length

// string = []const u8
const msg: []const u8 = "hello";
std.debug.print("len={d} text={s}\n", .{ msg.len, msg });
```

### 3.4 Control flow

```zig
if (x > 0) {
    // ...
} else if (x == 0) {
    // ...
} else {
    // ...
}

// switch must cover all cases (or use else)
switch (code) {
    0 => doZero(),
    1, 2 => doSmall(),
    else => doOther(),
}

for (items) |item| {
    _ = item;
}
for (items, 0..) |item, i| {
    _ = item;
    _ = i;
}

var i: usize = 0;
while (i < 10) : (i += 1) {
    // ...
}
```

### 3.5 Struct, method, enum, union

```zig
const Point = struct {
    x: f64,
    y: f64,

    // read-only method
    pub fn length(self: Point) f64 {
        return @sqrt(self.x * self.x + self.y * self.y);
    }

    // mutating method
    pub fn scale(self: *Point, k: f64) void {
        self.x *= k;
        self.y *= k;
    }
};

const Color = enum { red, green, blue };

const Shape = union(enum) {
    circle: f64,
    rect: struct { w: f64, h: f64 },

    pub fn area(self: Shape) f64 {
        return switch (self) {
            .circle => |r| std.math.pi * r * r,
            .rect => |rc| rc.w * rc.h,
        };
    }
};
```

Method receiver cheat sheet:

- `self: T` → read only, copy/view
- `self: *T` → will mutate
- `self: *const T` → read only, no copy of big structs

Heap-allocated struct (ALWAYS use struct literal):

```zig
const Node = struct {
    id: u32,
    next: ?*Node,
};

const node = try gpa.create(Node);
defer gpa.destroy(node);

// RIGHT: struct literal initializes every field
node.* = .{
    .id = 1,
    .next = null,
};

// WRONG:
// node.id = 1; (leaves new/other fields uninitialized garbage memory!)
```

### 3.6 Errors

```zig
const AppError = error{
    NotFound,
    BadInput,
};

fn parse(n: i32) AppError!i32 {
    if (n < 0) return error.BadInput;
    return n * 2;
}

fn demo() !void {
    // bubble up
    const a = try parse(3);

    // handle here
    const b = parse(-1) catch |err| {
        std.debug.print("err={t}\n", .{err});
        return;
    };

    _ = a;
    _ = b;
}
```

Cleanup:

```zig
fn load(gpa: std.mem.Allocator) ![]u8 {
    const buf = try gpa.alloc(u8, 100);
    errdefer gpa.free(buf); // only if this fn returns error

    // ... fill buf ...
    return buf; // caller owns memory
}
```

- `defer` → always runs at end of scope (LIFO order)
- `errdefer` → runs only on error path (put on IMMEDIATE line after resource acquisition)
- NEVER write `catch {}` or `catch |_| {}`

Growing a buffer under `defer free` (NO double-free):

```zig
// WRONG: if second alloc fails with OOM, defer frees already-freed ptr!
// gpa.free(buf);
// buf = try gpa.alloc(u8, new_size);

// RIGHT: use realloc:
buf = try gpa.realloc(buf, new_size);

// OR allocate to a temporary first:
const new_buf = try gpa.alloc(u8, new_size);
gpa.free(buf);
buf = new_buf;
```

### 3.7 comptime (generics)

```zig
fn maxValue(comptime T: type, a: T, b: T) T {
    if (a > b) return a;
    return b;
}

// use: maxValue(i32, 3, 7)
```

### 3.8 Tests

```zig
test "add works" {
    try std.testing.expectEqual(@as(i32, 4), 2 + 2);
}
```

Run: `zig build test`

### 3.9 Safe casting & numbers (never panic on external data)

Zig panics at runtime on invalid casts in safe builds:

```zig
// 1. Integer narrowing (@intCast panics if val < 0 or val > max):
if (val > std.math.maxInt(u8)) return error.ValueOutOfRange;
const small: u8 = @intCast(val);

// 2. Float to int (@intFromFloat panics on NaN, Inf, or overflow):
if (!std.math.isFinite(f) or f < 0.0 or f > 1e15) return error.InvalidNumber;
const ms: u64 = @intFromFloat(f);

// 3. Integer to enum (@enumFromInt panics if tag is undefined):
// WRONG: const mode: Mode = @enumFromInt(raw);
// RIGHT:
const mode = std.meta.intToEnum(Mode, raw) catch return error.InvalidMode;

// 4. File descriptors (0 is stdin! Only negative is invalid):
if (fd < 0) return error.BadFd; // NOT fd <= 0
```

---

## 4. Containers (lists and maps)

**Always unmanaged style in 0.16.**

### 4.1 ArrayList

```zig
var list: std.ArrayList(u32) = .empty;
defer list.deinit(gpa);

try list.append(gpa, 10);
try list.append(gpa, 20);
try list.appendSlice(gpa, &.{ 30, 40 });

std.debug.print("len={d} item0={d}\n", .{ list.items.len, list.items[0] });

// iterate
for (list.items) |item| {
    _ = item;
}
```

WRONG:

```zig
// var list = std.ArrayList(u32).init(gpa);  // OLD
// var list: std.ArrayList(u32) = .{};       // compile error
```

Pointer safety: `append()` reallocates the backing buffer!
NEVER hold a pointer to `list.items[i]` across any call that can append or mutate the list (dangling pointer / use-after-free).
If pointers to elements must stay stable, store pointers: `std.ArrayList(*MyStruct)`.

### 4.2 Hash maps

Prefer unmanaged:

```zig
// string key
var map: std.StringHashMapUnmanaged(u32) = .empty;
defer map.deinit(gpa);

try map.put(gpa, "one", 1);
try map.put(gpa, "two", 2);

if (map.get("one")) |v| {
    std.debug.print("{d}\n", .{v});
}

// auto key (ints, simple types)
var nums: std.AutoHashMapUnmanaged(u32, []const u8) = .empty;
defer nums.deinit(gpa);
try nums.put(gpa, 1, "a");
```

Array hash map (keeps insert order):

```zig
var ordered: std.array_hash_map.Auto(u32, u32) = .empty;
defer ordered.deinit(gpa);
try ordered.put(gpa, 10, 100);
```

---

## 5. I/O with `std.Io`

Pass `io` everywhere.

### 5.1 Write and read a file

```zig
pub fn main(init: std.process.Init) !void {
    const gpa = init.gpa;
    const io = init.io;

    const cwd = std.Io.Dir.cwd();

    // write
    try cwd.writeFile(io, .{
        .sub_path = "out.txt",
        .data = "hello\n",
    });

    // read whole file (limit size!)
    const data = try cwd.readFileAlloc(io, "out.txt", gpa, .limited(1024 * 1024));
    defer gpa.free(data);

    std.debug.print("{s}", .{data});
}
```

### 5.2 Open file + reader

```zig
const file = try std.Io.Dir.cwd().openFile(io, "out.txt", .{});
defer file.close(io);

var buf: [1024]u8 = undefined;
const r = file.reader(io, &buf);
// use r.interface (std.Io.Reader) for reading APIs
_ = r;
```

### 5.3 Sleep

```zig
// 10 milliseconds
try std.Io.sleep(io, .fromMilliseconds(10), .awake);
```

Clocks: `.real`, `.awake`, `.boot` (see std docs if needed). Prefer `.awake`.

### 5.4 Stdout writer

```zig
const Io = std.Io;

var stdout_buffer: [1024]u8 = undefined;
var stdout_writer: Io.File.Writer = .init(.stdout(), io, &stdout_buffer);
const w = &stdout_writer.interface;

try w.print("hello {s}\n", .{"world"});
try w.flush();
```

### 5.5 String helpers

```zig
// find substring → optional index
if (std.mem.find(u8, hay, "zig")) |idx| {
    std.debug.print("at {d}\n", .{idx});
}

// split once
if (std.mem.cut(u8, "a=b", "=")) |parts| {
    const key = parts[0];
    const val = parts[1];
    _ = key;
    _ = val;
}

// compare
if (std.mem.eql(u8, a, b)) {
    // equal
}

// Unicode UTF-8 <-> UTF-16 (built-in std.unicode):
// Allocate null-terminated UTF-16 from UTF-8:
const u16_z = try std.unicode.utf8ToUtf16LeAllocZ(gpa, "hello");
defer gpa.free(u16_z);

// Fixed buffer UTF-8 -> UTF-16 (dest must be >= 2 * src.len + 1):
var u16_buf: [128]u16 = undefined;
const u16_len = try std.unicode.utf8ToUtf16Le(&u16_buf, "hello");

// Fixed buffer UTF-16 -> UTF-8 (dest must be >= 3 * utf16.len + 1):
var u8_buf: [128]u8 = undefined;
const u8_len = try std.unicode.utf16LeToUtf8(&u8_buf, u16_buf[0..u16_len]);
_ = u8_len;
```

### 5.6 Subprocesses (`std.process.spawn`)

```zig
var child = try std.process.spawn(io, .{
    .argv = &.{ "echo", "hello" },
});
const term = try child.wait(io);
_ = term;
```

Do NOT use `std.process.Child.init` (removed in 0.16).

### 5.7 Fixed buffer Reader and Writer & safe formatting

`std.io` namespace and `fixedBufferStream` are REMOVED in 0.16. Use `.fixed`:

```zig
// write to fixed array buffer
var buf: [1024]u8 = undefined;
var w = std.Io.Writer.fixed(&buf);
try w.print("hello {s}\n", .{"world"});
const written: []const u8 = w.buffered();

// read from fixed slice
var r = std.Io.Reader.fixed("12345");
const slice = try r.take(5); // take N bytes

// Formatting strings safely:
// NEVER use `catch unreachable` on bufPrint — if text overflows, it PANICS!
var str_buf: [64]u8 = undefined;
const str = std.fmt.bufPrint(&str_buf, "id={d}", .{id}) catch return error.BufferTooSmall;

// Dynamic string formatting (preferred for variable or unknown lengths):
const heap_str = try std.fmt.allocPrint(gpa, "user={s}:{d}", .{ name, id });
defer gpa.free(heap_str);
```

### 5.8 JSON parsing and formatting

`std.json.stringify` is REMOVED in 0.16. Use `std.json.fmt`:

```zig
const Config = struct { name: []const u8, port: u16 };

// parse
const parsed = try std.json.parseFromSlice(Config, gpa, "{\"name\":\"app\",\"port\":8080}", .{});
defer parsed.deinit();

// format into print / logger / writer
std.debug.print("json: {}\n", .{std.json.fmt(parsed.value, .{})});
```

### 5.9 Mutex synchronization (`std.Io.Mutex`)

`std.Thread.Mutex` is REMOVED in 0.16. Use `std.Io.Mutex`:

```zig
var mutex: std.Io.Mutex = .init;
try mutex.lock(io);
defer mutex.unlock(io);
```

---

## 6. Full program templates

### 6.1 CLI: print args + HOME

`src/main.zig`:

```zig
const std = @import("std");

pub fn main(init: std.process.Init) !void {
    const arena = init.arena.allocator();
    const args = try init.minimal.args.toSlice(arena);

    for (args, 0..) |arg, i| {
        std.debug.print("{d}: {s}\n", .{ i, arg });
    }

    if (init.environ_map.get("HOME")) |home| {
        std.debug.print("HOME={s}\n", .{home});
    }
}
```

### 6.2 List + map + file

`src/main.zig`:

```zig
const std = @import("std");

pub fn main(init: std.process.Init) !void {
    const gpa = init.gpa;
    const io = init.io;

    var list: std.ArrayList(u32) = .empty;
    defer list.deinit(gpa);
    try list.append(gpa, 1);
    try list.append(gpa, 2);
    try list.append(gpa, 3);

    var map: std.StringHashMapUnmanaged(u32) = .empty;
    defer map.deinit(gpa);
    try map.put(gpa, "sum", 0);

    var sum: u32 = 0;
    for (list.items) |n| sum += n;
    try map.put(gpa, "sum", sum);

    const cwd = std.Io.Dir.cwd();
    try cwd.writeFile(io, .{
        .sub_path = "sum.txt",
        .data = "ok\n",
    });

    std.debug.print("sum={d}\n", .{map.get("sum").?});
}
```

### 6.3 Library function style (tagged union)

```zig
const std = @import("std");

const Shape = union(enum) {
    circle: f64,
    rect: struct { w: f64, h: f64 },

    pub fn area(self: Shape) f64 {
        return switch (self) {
            .circle => |r| std.math.pi * r * r,
            .rect => |rc| rc.w * rc.h,
        };
    }
};

test "area" {
    const c: Shape = .{ .circle = 2.0 };
    try std.testing.expect(c.area() > 12.0);
}
```

---

## 7. Build system

### 7.1 Fast start

```sh
zig init
zig build
zig build run
zig build test
```

### 7.2 Minimal `build.zig` (executable only)

```zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const root_module = b.createModule(.{
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });

    const exe = b.addExecutable(.{
        .name = "app",
        .root_module = root_module,
    });
    b.installArtifact(exe);

    const run_step = b.step("run", "Run the app");
    const run_cmd = b.addRunArtifact(exe);
    run_step.dependOn(&run_cmd.step);
    run_cmd.step.dependOn(b.getInstallStep());
    if (b.args) |args| run_cmd.addArgs(args);

    const unit_tests = b.addTest(.{
        .root_module = root_module,
    });
    const run_unit_tests = b.addRunArtifact(unit_tests);
    const test_step = b.step("test", "Run tests");
    test_step.dependOn(&run_unit_tests.step);
}
```

### 7.3 Minimal `build.zig.zon`

```zig
.{
    .name = .app,
    .version = "0.0.0",
    .fingerprint = 0x0123456789abcdef, // run `zig build` once; use the fingerprint it prints
    .minimum_zig_version = "0.16.0",
    .dependencies = .{},
    .paths = .{
        "build.zig",
        "build.zig.zon",
        "src",
    },
}
```

If fingerprint wrong, compiler prints the correct value. Paste it.

### 7.4 C headers with `addTranslateC`

`src/c_includes.h`:

```c
#include <stdio.h>
```

In `build.zig`:

```zig
const translate_c = b.addTranslateC(.{
    .root_source_file = b.path("src/c_includes.h"),
    .target = target,
    .optimize = optimize,
});
// translate_c.linkSystemLibrary("m", .{}); // if needed

const c_mod = translate_c.createModule();
root_module.addImport("c", c_mod);
```

In Zig:

```zig
const c = @import("c");
// call C functions from c.
```

Do NOT use `@cImport`.

### 7.5 C string interop rules

1. Zig slice (`[]const u8`) has length, NO null terminator.
2. C functions (`const char*`) require a null terminator `\x00`.

   ```zig
   // Pass Zig string to C function:
   const c_path = try gpa.dupeZ(u8, zig_path);
   defer gpa.free(c_path);
   _ = c.some_c_function(c_path.ptr);
   ```

3. C preflight buffer sizing: if a C API reports needed length `N` (excluding NUL), allocate `N + 1` for the terminator!
4. Read C string to Zig slice:

   ```zig
   if (c_ptr) |ptr| {
       const slice: []const u8 = std.mem.span(ptr);
       _ = slice;
   }
   ```

---

## 8. OLD Zig → 0.16 (migration table)

| Old (do not use) | New (0.16) |
| --- | --- |
| `pub fn main() !void` | `pub fn main(init: std.process.Init) !void` |
| `var gpa = std.heap.GeneralPurposeAllocator(.{}){};` in main | `const gpa = init.gpa;` |
| `std.heap.page_allocator` everywhere in apps | prefer `init.gpa` / `init.arena` |
| `std.process.argsAlloc` / `getArgsAlloc` | `try init.minimal.args.toSlice(arena)` |
| `std.process.getEnvVarOwned` | `init.environ_map.get("KEY")` |
| `std.fs.cwd().openFile(path, .{})` | `std.Io.Dir.cwd().openFile(io, path, .{})` |
| `std.fs.cwd().readFileAlloc(allocator, path, max)` | `std.Io.Dir.cwd().readFileAlloc(io, path, gpa, .limited(max))` |
| `file.close()` | `file.close(io)` |
| `std.time.sleep(ns)` | `try std.Io.sleep(io, .fromNanoseconds(ns), .awake)` |
| `std.net.*` | `std.Io.net.*` via `io` |
| `std.Thread.Mutex` (in async code) | `std.Io.Mutex` |
| `std.Thread.Pool` | `std.Io.async` / `std.Io.Group` |
| `var list = std.ArrayList(T).init(allocator)` | `var list: std.ArrayList(T) = .empty;` |
| `try list.append(x)` | `try list.append(gpa, x)` |
| `list.deinit()` | `list.deinit(gpa)` |
| `var map = std.StringHashMap(T).init(allocator)` | `var map: std.StringHashMapUnmanaged(T) = .empty;` |
| `std.AutoArrayHashMap(K,V)` | `std.array_hash_map.Auto(K,V)` |
| `= .{}` for empty list/map | `= .empty` |
| `@cImport({ @cInclude("x.h"); })` | `b.addTranslateC` + `@import("c")` |
| `std.mem.indexOf(u8, hay, needle)` | `std.mem.find(u8, hay, needle)` |
| `catch {}` / `catch \|_\| {}` | `try` or real handling |
| `std.posix.exit` | `std.process.exit` |
| `GenericReader` / `FixedBufferStream` / `std.io` | `std.Io.Reader.fixed` / `std.Io.Writer.fixed` |
| `std.process.Child.init(...)` | `std.process.spawn(io, .{.argv = ...})` |
| `std.json.stringify(...)` | `std.json.fmt(...)` |
| `std.Thread.Mutex` | `std.Io.Mutex` (`try mutex.lock(io)`) |
| `std.heap.ThreadSafeAllocator` | Removed (`ArenaAllocator` is thread-safe in 0.16) |
| print error with `{}` | print error with `{t}` |

---

## 9. Compiler errors → fix

| Error text | Fix |
| --- | --- |
| `missing struct field: items` | use `= .empty` not `= .{}` |
| `root source file struct 'xxx' has no member named 'main'` | export `pub fn main(init: std.process.Init) !void` |
| `unknown identifier: std.net` | use `std.Io.net` and pass `io` |
| `root source file struct 'std' has no member named 'io'` | `std.io` is removed; use `std.Io` and `std.Io.Writer.fixed` / `std.Io.Reader.fixed` |
| `root source file struct 'json' has no member named 'stringify'` | use `std.json.fmt(value, .{})` |
| `root source file struct 'Thread' has no member named 'Mutex'` | use `std.Io.Mutex` with `var mutex: std.Io.Mutex = .init; try mutex.lock(io);` |
| `no field or member function named 'read' in 'Io.Reader'` | use `try r.take(N)` or `r.readAlloc(gpa, N)` |
| `unknown identifier: @cImport` | use `addTranslateC` |
| `error: root_module` related in build | pass `.root_module = b.createModule(.{...})` into `addExecutable` |
| `pointless discard` | remove unused `_ = x` if `x` is used |
| `unused local constant` | use it, or `_ = name;` |
| `vector index must be a comptime-known value` | copy vector to array first: `const arr: [N]T = vec;` |
| `pointer to packed struct field cannot coerce` | copy field to local var, or use `extern struct` |
| fingerprint error in `build.zig.zon` | paste the fingerprint value from the error message |
| test timeout after 1.00s | `zig build test --test-timeout-scale=5.0` |
| `integer does not fit in destination type` | `@intCast` out of range — check bounds first (`if (v > max)`) |
| `float cannot fit into integer type` / NaN/Inf | `@intFromFloat` panic — check `std.math.isFinite(f)` |
| `enum tag value not found` | `@enumFromInt` invalid tag — use `std.meta.intToEnum(Enum, val)` |
| `use of uninitialized value` | initialize allocated struct with `p.* = .{ ... }` |

Verbose errors:

```sh
zig build -ferror-style=verbose_clear --multiline-errors
```

---

## 10. Packed structs / bitcast (only when needed)

```zig
// @bitCast only same bit size
const raw: u32 = 0x3F800000;
const f: f32 = @bitCast(raw);

// packed union needs backing int
const U = packed union(u32) {
    integer: u32,
    floating: f32,
};
```

Packed struct rules:

1. No pointer fields (store `usize`, convert with `@intFromPtr` / `@ptrFromInt`)
2. No `@Vector` fields
3. Prefer `extern struct` for C layouts

---

## 11. Idioms worth copying

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

---

## 12. Final checklist (before you stop)

- [ ] `main(init: std.process.Init) !void`
- [ ] Got `gpa`, `io`, `arena` from `init` when needed
- [ ] Every I/O call got `io`
- [ ] Every grow/free on list/map got `gpa`
- [ ] Containers started with `.empty`
- [ ] `defer x.deinit(gpa)` for owned containers
- [ ] No `catch {}`
- [ ] No `@cImport`
- [ ] No `std.fs` ambient I/O for new code (use `std.Io.Dir`)
- [ ] No `std.process.Child.init` (use `std.process.spawn(io, ...)`)
- [ ] No `std.io.fixedBufferStream` (use `std.Io.Writer.fixed` or `std.Io.Reader.fixed`)
- [ ] No `std.json.stringify` (use `std.json.fmt`)
- [ ] No `std.Thread.Mutex` (use `std.Io.Mutex` with `try mutex.lock(io)`)
- [ ] Initialized heap struct with `p.* = .{ ... }` struct literal
- [ ] No unchecked `@intCast` or `@intFromFloat` on external data
- [ ] Used `std.meta.intToEnum` for untrusted enum tags
- [ ] No `catch unreachable` on `std.fmt.bufPrint`
- [ ] No pointer held into `list.items` across `append()`
- [ ] Buffer growth under `defer free` uses `realloc` or temp alloc (no double-free)
- [ ] C string calls get null-terminated `[:0]u8` (allocated `len + 1`)
- [ ] `zig build` ok
- [ ] `zig build test` ok (if tests)

---

## 13. Commands cheat sheet

```sh
zig version          # must show 0.16.0
zig init             # scaffold project
zig build            # build
zig build run        # build + run
zig build run -- a b # run with args
zig build test       # tests
zig fmt .            # format sources
zig ast-check src/main.zig
```

---

## 14. What NOT to do

1. Do not invent `std.something` APIs not shown here.
2. Do not use blog/code from Zig 0.11–0.15 as truth.
3. Do not use managed container `.init(allocator)` style for new code.
4. Do not ignore compiler errors — they tell you the fix.
5. Do not write huge frameworks. Small clear functions. Pass `io` + `gpa`.
6. Do not use `std.process.Child.init`, `std.io.fixedBufferStream`, `std.json.stringify`, or `std.Thread.Mutex` — all removed in 0.16.
7. Do not initialize heap structs field-by-field after `allocator.create` — use `p.* = .{ ... }`.
8. Do not use unchecked `@intCast`, `@intFromFloat`, or `@enumFromInt` on external/untrusted inputs.
9. Do not use `catch unreachable` on `bufPrint`.
10. Do not hold element pointers while calling `list.append(...)`.
11. Do not `free(buf); buf = alloc(...);` when `defer free(buf)` is active.
12. Do not pass non-null-terminated slices to C APIs.
