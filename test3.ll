define i32 @main() #0 {
  %aVar = alloca i32
  %bVar = alloca i32
  %secret = call i32 () @SOURCE()
  store i32 %secret, ptr %aVar
  %a1 = load i32, ptr %aVar
  store i32 %a1, ptr %bVar
  %b1 = load i32, ptr %bVar
  call void @SINK(i32 %b1)
  ret i32 0
}

declare i32 @SOURCE()
declare void @SINK(i32)