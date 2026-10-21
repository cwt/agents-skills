# Language basics (Zig 0.16.0)

Companion reference for `zig-0160-development` skill. Load on demand.

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
- `errdefer` → runs only on error path (put on IMMEDIATE line after resource acquisition). NOTE: `errdefer` only runs if the function returns an error union. If an error is caught with `catch |err| { return; }` (returning `void` or a value), `errdefer` will NEVER run — place cleanup in the `catch` block!
- Multi-shot callbacks: in async loops or completion callbacks that re-queue work (e.g. partial writes), an unconditional `defer cleanup()` deallocates state while the next SQE is in flight. Guard cleanup with a latch: `var requeued = false; defer if (!requeued) cleanup(state);` (set `requeued = true` before returning on partial resubmission).
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

