define i32 @main() {
  %aVar = alloca i32
  store i32 0, ptr %aVar
  %a1 = load i32, ptr %aVar
  %ifTruth = icmp ne i32 %a1, 0
  br i1 %ifTruth, label %ifBody, label %afterIf

ifBody:
  %secret = call i32 (...) @SOURCE()
  store i32 %secret, ptr %aVar
  br label %afterIf

afterIf:
  %a2 = load i32, ptr %aVar
  call void @SINK(i32 %a2)
  ret i32 0
}

declare i32 @SOURCE(...)
declare void @SINK(i32)