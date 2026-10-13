define i32 @main() {
  %aVar = alloca i32
  %secret = call i32 () @SOURCE()
  store i32 %secret, ptr %aVar
  store i32 0, ptr %aVar
  %a1 = load i32, ptr %aVar
  call void @SINK(i32 %a1)
  ret i32 0
}

declare i32 @SOURCE()
declare void @SINK(i32 )