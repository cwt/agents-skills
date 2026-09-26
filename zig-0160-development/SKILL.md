---
name: zig-0160-development
description: Zig 0.16.0 coding skill for small local LLMs (9B-27B). Short rules, one true style, full copy-paste programs. Covers main(init), std.Io, unmanaged containers, build.zig, tests, C headers, and a code-review bug-hunting checklist. Every snippet compiled against real Zig 0.16.0.
---

# Zig 0.16.0 Skill (for small local LLMs)

You know NOTHING about Zig. Use ONLY this file.

Target version: **Zig 0.16.0** only. Every code block below was compiled with
`zig 0.16.0` on x86_64-linux. If a compiler error contradicts this file,
trust the compiler — then tell the user this file was wrong.

Ground truth is local, not this file:

- `zig version` must print `0.16.0`.
- `zig env` → `.std_dir` is the standard library source. `grep` it to verify any API.
- `zig std` starts a local HTTP server with the std library docs.

---

## 0. How you work (MUST follow)

1. Copy patterns from this file. Do not invent APIs.
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
| 8 | No `@cImport` (deprecated) | `@cImport(@cInclude(...))` | `b.addTranslateC` in `build.zig` |
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

Switch extras (0.16): packed structs/unions work as prong items; union tag
captures need no `inline`; but a prong whose captures are ALL discarded is a
compile error — remove the capture.

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

Custom formatting (must use `{f}`, NOT `{}`):

```zig
const P = struct {
    x: i32,
    y: i32,

    // EXACT signature — 2 args, no options param
    pub fn format(self: P, w: *std.Io.Writer) std.Io.Writer.Error!void {
        try w.print("({d},{d})", .{ self.x, self.y });
    }
};

std.debug.print("{f}\n", .{P{ .x = 1, .y = 2 }}); // (1,2)
// std.debug.print("{}\n",  .{P{ .x = 1, .y = 2 }}); // WRONG: prints .{ .x = 1, .y = 2 }
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
// node.id = 1; (leaves other fields uninitialized garbage memory!)
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

Note: error sets CANNOT be created at comptime anymore. Declare them
explicitly with `error{ ... }`.

### 3.8 Tests

```zig
test "add works" {
    try std.testing.expectEqual(@as(i32, 4), 2 + 2);
}

// I/O in tests: std.testing.io (only exists in `zig test` builds!)
test "sleep works" {
    const io = std.testing.io;
    try std.Io.sleep(io, .fromMilliseconds(1), .awake);
}
```

Run: `zig build test` or `zig test file.zig` for a single file.
Use `std.testing.allocator` in every allocating test — a leak fails the run.

### 3.9 Safe casting & numbers (never panic on external data)

```zig
// 1. Integer narrowing (@intCast panics if val < 0 or val > max):
if (val > std.math.maxInt(u8)) return error.ValueOutOfRange;
const small: u8 = @intCast(val);

// 2. Float -> int: prefer @trunc with explicit result type:
if (!std.math.isFinite(f) or f < 0.0 or f > 1e15) return error.InvalidNumber;
const ms: u64 = @trunc(f);

// 2b. Small int -> float coerces implicitly when every value fits:
const small_u8: u8 = 7;
const as_f: f32 = small_u8; // no @floatFromInt needed

// 3. Integer -> enum (returns ?Enum, NOT an error union):
// WRONG: const mode: Mode = @enumFromInt(raw);
// RIGHT:
const mode = std.enums.fromInt(Mode, raw) orelse return error.InvalidMode;

// 4. File descriptors (0 is stdin! Only negative is invalid):
if (fd < 0) return error.BadFd; // NOT fd <= 0
```

`{t}` prints errors/enums/unions (`{t}` on an error prints its name).
`{t}` does NOT work on optionals — unwrap first.

### 3.10 Allocators

```zig
// In main: init.gpa is provided (a DebugAllocator behind the scenes).
// In tests: use the leak-checking test allocator:
test "alloc" {
    const gpa = std.testing.allocator;
    const buf = try gpa.alloc(u8, 16);
    defer gpa.free(buf);
}

// If you ever need your own (rare — prefer init.gpa):
var dbg: std.heap.DebugAllocator(.{}) = .init;
defer _ = dbg.deinit();
const gpa2 = dbg.allocator();
```

`std.heap.GeneralPurposeAllocator` and `std.heap.ThreadSafeAllocator` are
gone in 0.16 — `DebugAllocator` replaced them (and is thread-safe).

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

// preallocate when you know the size:
try list.ensureTotalCapacity(gpa, 100);

std.debug.print("len={d} item0={d}\n", .{ list.items.len, list.items[0] });

// iterate
for (list.items) |item| {
    _ = item;
}

// reuse the buffer without freeing:
list.clearRetainingCapacity();
```

WRONG:

```zig
// var list: std.ArrayList(u32) = .{};       // compile error
// var list = std.ArrayList(u32).init(gpa);  // old managed style, gone
```

Pointer safety: `append()` reallocates the backing buffer!
NEVER hold a pointer to `list.items[i]` across any call that can append or mutate the list (dangling pointer / use-after-free).
If pointers to elements must stay stable, store pointers: `std.ArrayList(*MyStruct)`.

### 4.2 Hash maps

TRAP: the no-suffix names are MANAGED (`init(gpa)`, `put(k, v)`, `deinit()`).
For the unmanaged style this skill uses, you MUST use the `...Unmanaged` names:

```zig
// string key — unmanaged
var map: std.StringHashMapUnmanaged(u32) = .empty;
defer map.deinit(gpa);

try map.put(gpa, "one", 1);
try map.put(gpa, "two", 2);

if (map.get("one")) |v| {
    std.debug.print("{d}\n", .{v});
}

// auto key (ints, simple types) — unmanaged
var nums: std.AutoHashMapUnmanaged(u32, []const u8) = .empty;
defer nums.deinit(gpa);
try nums.put(gpa, 1, "a");
```

WRONG:

```zig
// var map: std.StringHashMap(u32) = .empty;  // no member named 'empty'!
// try map.put(gpa, "one", 1);              // managed put takes NO allocator
```

Array hash map (keeps insert order):

```zig
var ordered: std.array_hash_map.Auto(u32, u32) = .empty;
defer ordered.deinit(gpa);
try ordered.put(gpa, 10, 100);
```

### 4.3 Priority queue

```zig
fn lessThan(a: u32, b: u32) std.math.Order {
    return std.math.order(a, b);
}

const MinHeap = std.PriorityQueue(u32, void, lessThan);
var queue: MinHeap = .empty;
defer queue.deinit(gpa);

try queue.push(gpa, 5);
try queue.push(gpa, 1);
const smallest = queue.pop(); // ?u32
_ = smallest;
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

### 5.2 Open file + reader / writer

`file.reader` and `file.writer` take BOTH `io` and the buffer:

```zig
const file = try std.Io.Dir.cwd().openFile(io, "out.txt", .{});
defer file.close(io);

// reading
var read_buf: [1024]u8 = undefined;
var r = file.reader(io, &read_buf);
const chunk = try r.interface.take(5); // read up to N bytes
_ = chunk;

// writing (needs its own buffer)
var write_buf: [1024]u8 = undefined;
var w = file.writer(io, &write_buf);
try w.interface.print("data {d}\n", .{42});
try w.interface.flush();
```

### 5.3 Sleep

```zig
// 10 milliseconds, monotonic clock
try std.Io.sleep(io, .fromMilliseconds(10), .awake);
```

Clocks: `.real` (wall time), `.awake` (monotonic since boot/wake — prefer),
`.boot` (monotonic since boot).

### 5.4 Stdout writer

```zig
const Io = std.Io;

var stdout_buffer: [1024]u8 = undefined;
var stdout_writer: Io.File.Writer = .init(.stdout(), io, &stdout_buffer);
const w = &stdout_writer.interface;

try w.print("hello {s}\n", .{"world"});
try w.flush();
```

### 5.5 Growable string (Writer.Allocating)

The idiom for building a string of unknown length:

```zig
var aw: std.Io.Writer.Allocating = .init(gpa);
defer aw.deinit();

try aw.writer.print("user={s}:{d}", .{ name, id });
const s: []u8 = aw.written(); // borrow; valid until deinit/toOwnedSlice
// const owned: []u8 = try aw.toOwnedSlice(); // take ownership instead
```

`aw.writer` is a FIELD (a `*std.Io.Writer`), not a method.

### 5.6 String helpers

```zig
// find substring -> optional index
if (std.mem.find(u8, hay, "zig")) |idx| {
    std.debug.print("at {d}\n", .{idx});
}

// split once -> optional tuple (must unwrap)
if (std.mem.cut(u8, "a=b", "=")) |parts| {
    const key = parts[0];
    const val = parts[1];
    _ = key;
    _ = val;
}

// strip a known prefix/suffix -> optional
const rest = std.mem.cutPrefix(u8, "pre_x", "pre_"); // ?"x"
const base = std.mem.cutSuffix(u8, "x_suf", "_suf"); // ?"x"

// trim leading spaces (NOT trimLeft — renamed)
const t = std.mem.trimStart(u8, "  hi  ", " ");

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

### 5.7 Subprocesses

```zig
// simple: spawn and wait
var child = try std.process.spawn(io, .{
    .argv = &.{ "echo", "hello" },
});
const term = try child.wait(io);
_ = term;

// with pipes:
var child2 = try std.process.spawn(io, .{
    .argv = &.{ "cat" },
    .stdin = .pipe,
    .stdout = .pipe,
    .stderr = .ignore,
});
// ... write to child2.stdin, read from child2.stdout ...
const term2 = try child2.wait(io);
_ = term2;

// run a command and capture stdout/stderr (you own and must free them)
const res = try std.process.run(gpa, io, .{ .argv = &.{ "echo", "yo" } });
defer gpa.free(res.stdout);
defer gpa.free(res.stderr);
std.debug.print("{s}", .{res.stdout});
```

Do NOT use `std.process.Child.init` (removed in 0.16).

### 5.8 Fixed buffer Reader and Writer & safe formatting

`std.io` namespace and `fixedBufferStream` are REMOVED in 0.16. Use `.fixed`:

```zig
// write to fixed array buffer
var buf: [1024]u8 = undefined;
var w = std.Io.Writer.fixed(&buf);
try w.print("hello {s}\n", .{"world"});
const written: []u8 = w.buffered();

// read from fixed slice
var r = std.Io.Reader.fixed("12345");
const slice = try r.take(5); // take N bytes

// Formatting strings safely:
// NEVER use `catch unreachable` on bufPrint — if text overflows, it PANICS!
var str_buf: [64]u8 = undefined;
const str = std.fmt.bufPrint(&str_buf, "id={d}", .{id}) catch return error.BufferTooSmall;

// null-terminated variant (bufPrintZ still exists; bufPrintSentinel is the modern name):
var z_buf: [64]u8 = undefined;
const z = try std.fmt.bufPrintSentinel(&z_buf, "id={d}", .{id}, 0);
_ = z;

// Dynamic string formatting (preferred for variable or unknown lengths):
const heap_str = try std.fmt.allocPrint(gpa, "user={s}:{d}", .{ name, id });
defer gpa.free(heap_str);
```

### 5.9 JSON parsing and formatting

`std.json.stringify` is REMOVED in 0.16. Use `std.json.fmt` with `{f}`:

```zig
const Config = struct { name: []const u8, port: u16 };

// parse
const parsed = try std.json.parseFromSlice(Config, gpa, "{\"name\":\"app\",\"port\":8080}", .{});
defer parsed.deinit();

// format — MUST be {f}, not {} ({} prints a struct dump!)
std.debug.print("{f}\n", .{std.json.fmt(parsed.value, .{})});
```

### 5.10 Mutex synchronization (`std.Io.Mutex`)

`std.Thread.Mutex` is REMOVED in 0.16. Use `std.Io.Mutex`:

```zig
var mutex: std.Io.Mutex = .init;
try mutex.lock(io); // lock returns an error — try is required
defer mutex.unlock(io);
```

### 5.11 Randomness

```zig
// basic random bytes (may use stored RNG state)
var buf: [16]u8 = undefined;
io.random(&buf);

// always-syscall secure bytes (can fail)
try io.randomSecure(&buf);

// a std.Random interface backed by io:
var src: std.Random.IoSource = .{ .io = io };
const rng = src.interface();
const n: u64 = rng.int(u64);
```

`std.crypto.random` is gone. There is no `.init(io)` on `IoSource` —
construct the struct literal directly.

### 5.12 Networking (`std.Io.net`)

`std.net` is REMOVED. Networking lives under `std.Io.net` and needs `io`:

```zig
// connect: `mode` is REQUIRED in ConnectOptions
const stream = try addr.connect(io, .{ .mode = .stream });
defer stream.close(io);

// listen: returns a Server; accept in a loop
const server = try addr.listen(io, .{});
```

`std.Io.net.Stream` is the TCP-stream type; `std.Io.net.Server` accepts
connections. Read/write through the stream's reader/writer interface.

### 5.13 Concurrency: `io.async` and `Future`

`std.Thread.Pool` is REMOVED. Spawn fibers with `io.async`:

```zig
fn worker(n: u32) u32 {
    return n * 2;
}

var future = io.async(worker, .{21});
defer _ = future.cancel(io); // idempotent; cancels if not done
const result = future.await(io); // u32 = 42
// if the fn returns an error union: const r = try future.await(io);
```

- `io.async(fn, .{args})` — may run synchronously; use `io.concurrent` when it
  MUST run concurrently (can fail with `error.ConcurrencyUnavailable`).
- `Future(T)` has `.await(io)` and `.cancel(io)`, both idempotent.
- `std.Io.Group` manages many tasks with shared lifetime.
- Cancelation is spelled with ONE `l`: `error.Canceled`, `Canceled`, `Canceling`.
- Most I/O error sets now include `error.Canceled`.

### 5.14 Logging

```zig
std.log.info("started on port {d}", .{port});
std.log.warn("slow request: {d}ms", .{ms});
```

---

## 6. Full program templates

### 6.1 CLI: print args + HOME

`src/main.zig`:

```zig
const std = @import("std");

pub fn main(init: std.process.Init) !void {
    var it = std.process.Args.Iterator.init(init.minimal.args);
    var i: usize = 0;
    while (it.next()) |arg| : (i += 1) {
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
zig init             # scaffold project
zig version          # must show 0.16.0
zig env              # shows .std_dir, .lib_dir, cache paths
zig fmt --check .    # check formatting
zig build            # build
zig build run        # build + run
zig build run -- a b # run with args
zig build test       # tests
zig test src/x.zig   # test one file directly
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

Libraries: `b.addLibrary(...)` replaced `addStaticLibrary`/`addSharedLibrary`
(linkage chosen via `.linkage`).

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

- `.fingerprint` is REQUIRED in 0.16; `.name` must be an enum literal (`.app`, not `"app"`).
- If the fingerprint is wrong, the compiler prints the correct value. Paste it.
- Dependencies are fetched into a project-local `zig-pkg/` dir (don't commit it).

### 7.4 Add a dependency

```zig
// build.zig.zon
.dependencies = .{
    .some_lib = .{
        .url = "https://example.com/some_lib.tar.gz",
        .hash = "...", // `zig build` prints the correct hash on first fetch
    },
},

// build.zig
const dep = b.dependency("some_lib", .{
    .target = target,
    .optimize = optimize,
});
root_module.addImport("some_lib", dep.module("some_lib"));
```

Temporarily override a package with a local fork:

```sh
zig build --fork=/path/to/local/fork
```

### 7.5 C headers with `addTranslateC`

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

Do NOT use `@cImport` (deprecated; will be removed).

### 7.6 C string interop rules

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

### 7.7 Cross-compilation

```sh
zig build -Dtarget=x86_64-linux-musl      # static Linux binary
zig build -Dtarget=aarch64-macos          # Apple Silicon
zig build -Dtarget=x86_64-windows         # Windows
```

Target triple: `<arch>-<os>[-<abi>]`, e.g. `x86_64-linux-musl`,
`aarch64-linux-gnu`, `x86_64-windows-gnu`.

### 7.8 Test flags

```sh
zig build test --test-timeout 500ms   # kill+restart tests that hang
zig build test --test-timeout-scale=5 # multiply the default 1s timeout
```

---

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
| `try list.append(x)` | `try list.append(gpa, x)` |
| `list.deinit()` | `list.deinit(gpa)` |
| `var map = std.StringHashMap(T).init(gpa)` (managed) | `var map: std.StringHashMapUnmanaged(T) = .empty;` |
| `std.AutoArrayHashMap(K,V)` | `std.array_hash_map.Auto(K,V)` |
| `std.PriorityQueue` `add` / `remove` | `push` / `pop`; init with `.empty` |
| `= .{}` for empty list/map | `= .empty` |
| `@cImport({ @cInclude("x.h"); })` | `b.addTranslateC` + `@import("c")` (deprecated) |
| `std.mem.indexOf(u8, hay, needle)` | `std.mem.find(u8, hay, needle)` |
| `std.mem.trimLeft` | `std.mem.trimStart` |
| `catch {}` / `catch \|_\| {}` | `try` or real handling |
| `std.posix.exit` | `std.process.exit` |
| `GenericReader` / `FixedBufferStream` / `std.io` | `std.Io.Reader.fixed` / `std.Io.Writer.fixed` |
| `std.process.Child.init(...)` | `std.process.spawn(io, .{.argv = ...})` |
| `std.process.Child.run(alloc, io, ...)` | `std.process.run(gpa, io, .{.argv = ...})` |
| `std.json.stringify(...)` | `std.json.fmt(value, .{})` with `{f}` |
| `std.fmt.bufPrintZ` | still exists; `std.fmt.bufPrintSentinel` is the modern name |
| `std.meta.intToEnum(E, v)` | `std.enums.fromInt(E, v) orelse ...` (returns `?E`) |
| `{}` on a type with `format()` | `{f}` |
| `@Type(.{ .int = ... })` | `@Int(.unsigned, 10)` and friends (see §10) |
| print error with `{}` | print error with `{t}` |

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
- [ ] Buffer growth under `defer free` uses `realloc` or temp alloc (no double-free)
- [ ] C string calls get null-terminated `[:0]u8` (allocated `len + 1`)
- [ ] `zig fmt --check .` ok
- [ ] `zig build` ok
- [ ] `zig build test` ok (if tests)

---

## 14. Commands cheat sheet

```sh
zig version          # must show 0.16.0
zig env              # toolchain + std paths
zig init             # scaffold project
zig build            # build
zig build run        # build + run
zig build run -- a b # run with args
zig build test       # tests
zig build test --test-timeout 500ms
zig build test --fuzz               # fuzz tests using std.testing.fuzz
zig test src/x.zig   # test one file
zig fmt .            # format sources
zig fmt --check .    # check formatting
zig ast-check src/main.zig
zig std              # local std docs HTTP server
```

---

## 15. What NOT to do

1. Do not invent `std.something` APIs not shown here.
2. Do not use blog/code from Zig 0.11–0.15 as truth.
3. Do not use managed container `.init(allocator)` style for new code.
4. Do not ignore compiler errors — they tell you the fix.
5. Do not write huge frameworks. Small clear functions. Pass `io` + `gpa`.
6. Do not use `std.process.Child.init`, `std.io.fixedBufferStream`, `std.json.stringify`, or `std.Thread.Mutex` — all removed in 0.16.
7. Do not initialize heap structs field-by-field after `allocator.create` — use `p.* = .{ ... }`.
8. Do not use unchecked `@intCast` or `@enumFromInt` on external/untrusted inputs.
9. Do not use `catch unreachable` on `bufPrint`.
10. Do not hold element pointers while calling `list.append(...)`.
11. Do not `free(buf); buf = alloc(...);` when `defer free(buf)` is active.
12. Do not pass non-null-terminated slices to C APIs.
13. Do not use `std.meta.intToEnum` (gone) — it's `std.enums.fromInt` now.
14. For CLI args use `init.minimal.args.toSlice(arena)` (returns `[]const [:0]const u8`) or iterate with `std.process.Args.Iterator` — never `std.process.argsAlloc` (removed in 0.16).
15. Do not use `std.crypto.random` — use `io.random` / `io.randomSecure`.
16. Do not print `std.json.fmt(...)` with `{}` — use `{f}`.
17. Do not assume `std.StringHashMap(T)` is unmanaged — it's the MANAGED wrapper; unmanaged is `std.StringHashMapUnmanaged(T)`.
18. Do not skip §16 when reviewing code you didn't write.

---

## 16. Reviewing Zig code (bug hunting)

When asked to review Zig code, follow this procedure:

1. Compile it first (`zig build`, or `zig build-exe file.zig`). Fix compile
   errors before hunting logic bugs.
2. Run the tests: `zig build test`. Leaks fail the run — the test allocator
   is your best bug finder.
3. Walk the bug catalog below. For each hit report: file:line, severity
   (critical / major / minor), what's wrong, and the fix.
4. Do not invent bugs. Only report ones you can point to.

### 16.1 Memory bugs

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

### 16.2 Pointer / slice bugs

| Smell | Check | Fix |
| --- | --- | --- |
| pointer into `list.items[i]` kept across `append` | dangling after realloc | store index, or store `*T` in the list |
| slice from `w.buffered()` used after more writes | silently overwritten | finish writing first, or copy |
| `const chunk = try r.take(5)` then `chunk[4]` | `take` returns UP TO N bytes | check `chunk.len` |
| slice escaping the scope that owns its buffer | use-after-free | extend the owner's lifetime |

### 16.3 Error-handling bugs

| Smell | Check | Fix |
| --- | --- | --- |
| `catch {}` / `catch \|_\| {}` | swallowed failure | `try`, or handle and log |
| `bufPrint(...) catch unreachable` | PANICS on overflow | return an error, or `allocPrint` |
| `switch` over an error set without `else` | misses new variants later | add `else` prong |
| `@intCast(x)` / `@enumFromInt(x)` on untrusted input | panic on bad data | bounds check / `std.enums.fromInt` + `orelse` |
| `child.wait(io)` result ignored | zombie process | always `try child.wait(io)` |
| `try` missing on `future.await(io)` when fn returns `!T` | error silently dropped | `try` it |

### 16.4 I/O bugs

| Smell | Check | Fix |
| --- | --- | --- |
| writer used, no `flush()` | lost output | `try w.flush()` before close/return |
| `openFile` without `defer file.close(io)` | fd leak | defer immediately |
| `readFileAlloc(..., .limited(huge))` or unbounded | memory DoS on big files | small limit + handle `error.StreamTooLong` |
| `std.debug.print` in a hot loop | slow, unbuffered | buffered `Io.File.Writer` |

### 16.5 Concurrency bugs

| Smell | Check | Fix |
| --- | --- | --- |
| shared `var` mutated from `io.async` tasks | data race | guard with `std.Io.Mutex` (`try lock(io)`) |
| `io.async` assumed to run concurrently | it may run INLINE | `io.concurrent` when ordering matters (handle `error.ConcurrencyUnavailable`) |
| `future` never awaited/cancelled | leaked task resources | `defer _ = future.cancel(io)` |

### 16.6 Format / print bugs

| Smell | Check | Fix |
| --- | --- | --- |
| `{}` on `std.json.fmt(...)` or a custom `format()` | prints a struct dump | `{f}` |
| `{t}` on `?Error` / `?Enum` | compile error / wrong output | unwrap first |
| `{s}` on `[]const u16` | garbage | `std.unicode.utf16LeToUtf8` first |

### 16.7 0.16 API-misuse bugs

| Smell | Check | Fix |
| --- | --- | --- |
| `std.StringHashMap(T) = .empty` | managed type has no `.empty` | `StringHashMapUnmanaged` |
| `file.reader(&buf)` / `file.writer(&buf)` | missing `io` arg | `file.reader(io, &buf)` |
| `std.io.*`, `std.Thread.Mutex`, `std.json.stringify`, `std.process.Child.init` | all removed in 0.16 | see §8 migration table |
| `std.process.argsAlloc` | removed in 0.16 | `init.minimal.args.toSlice(arena)` or `std.process.Args.Iterator` |
| `std.meta.intToEnum` | gone | `std.enums.fromInt` |

### 16.8 C-interop bugs

| Smell | Check | Fix |
| --- | --- | --- |
| `[]const u8` passed to C `char*` | missing NUL terminator | `gpa.dupeZ(u8, s)` |
| C preflight returns `N`, buffer of `N` allocated | NUL written out of bounds | allocate `N + 1` |
| `std.mem.span(ptr)` on nullable C pointer | segfault on null | null-check first |

### 16.9 Review prompt (paste with the code)

```text
Review this Zig 0.16.0 code for bugs. For each issue give file:line,
severity (critical/major/minor), what's wrong, and the fix.
Check: memory ownership (defer/errdefer, double-free, leaks), list pointer
invalidation, error handling (no catch {}), I/O (flush, close, size limits),
concurrency races, format specifiers ({s}/{d}/{t}/{f}), API names against the
skill, C string termination. Do not invent bugs — only report ones you can
point to in the code.
```
