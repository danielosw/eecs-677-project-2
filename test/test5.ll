define i32 @main() {
  %aVar = alloca i32
  store i32 0, ptr %aVar
  br label %loop

loop:
  %loaded = load i32, ptr %aVar
  call void @SINK(i32 %loaded)
  %cond = icmp eq i32 0, 0
  br i1 %cond, label %body, label %exit

body:
  %secret = call i32 (...) @SOURCE()
  store i32 %secret, ptr %aVar
  br label %loop

exit:
  ret i32 0
}

declare i32 @SOURCE(...)
declare void @SINK(i32)
