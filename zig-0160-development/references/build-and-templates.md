# Templates, build system (Zig 0.16.0)

Companion reference. Load on demand.

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

Do NOT use `@cImport` — **removed in 0.17.0** (`error: invalid builtin
function: '@cImport'`). Use `b.addTranslateC` (§7.5), which is still available in
both 0.16 and 0.17.

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

5. Stealing C APIs: functions like `PyErr_SetRaisedException`, `PyTuple_SetItem`, etc. take ownership of the passed pointer. If the surrounding scope has `defer py_decref(x)` active, passing `x` causes a double-free on scope exit. You MUST pass `py_newref(x)` so the stealing transfer and the local defer each own distinct reference counts.

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

