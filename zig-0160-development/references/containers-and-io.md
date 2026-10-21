# Containers and I/O (Zig 0.16.0)

Companion reference. Load on demand.

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
Watch out for re-entrancy: calling external/foreign code (e.g. CPython `PyObject_RichCompareBool` or releasing objects via `decref` which can trigger `__del__`) while iterating `list.items` by slice can re-enter your code and append to the list. Use index-based loops (`while (i < list.items.len)`), hold temporary references to candidate elements, and re-check bounds after the call.
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
fn lessThan(context: void, a: u32, b: u32) std.math.Order {
    _ = context;
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

// Unicode UTF-8 <-> UTF-16 (built-in std.unicode).
// Fixed-buffer sizes must fit data + NUL: UTF-8 -> UTF-16 needs >= 2 * len + 1
// u16s, UTF-16 -> UTF-8 needs >= 3 * len + 1 u8s:
const u16_z = try std.unicode.utf8ToUtf16LeAllocZ(gpa, "hello");
defer gpa.free(u16_z);
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

// null-terminated variant: bufPrintZ was REMOVED in 0.17.0 — use bufPrintSentinel
// (identical signature in 0.16 and 0.17):
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

