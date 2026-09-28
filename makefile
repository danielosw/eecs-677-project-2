all:
	
clean:
	rm *.dot
	rm *.png
test:
	./graph test1.ll
	dot main.dot -o main.png -Tpng