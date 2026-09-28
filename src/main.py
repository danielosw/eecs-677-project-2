import argparse
import re
from operator import contains
from pathlib import Path

regex_define = re.compile(r"define .*? (.*?)\(")


def process_function(lines: list[str]) -> None:
	# STARTS BLOCK: define, LABELNAME:.
	# ENDS BLOCK: br, ret
	# jumps to block: br, call
	# step 1: go line by line, breaking into blocks
	# step 2: find jump points
	# step 3: output graph
	inblock = False
	blocknames: list[str] = []
	blocks: dict[str, list[str]] = {}
	connections: dict[str, list[str]] = {}
	currentname = ""
	functioname = ""
	currentcounter = 1
	for i in lines:
		if not inblock:
			# regex for checking for define
			define = regex_define.match(i)
			if define is not None:
				blocknames.append(define.group(1))
				inblock = True
				currentname = define.group(1)
				blocks[currentname] = []
				connections[currentname] = []
				functioname = currentname
				blocks[currentname].append(i)
				continue
			labels = re.match(r"(.*?):", i)
			if labels is not None:
				blocknames.append(labels.group(1))
				currentname = labels.group(1)
				blocks[currentname] = []
				connections[currentname] = []

				blocks[currentname].append(i)

				inblock = True
				continue
		else:
			# we are in a block
			# so look for end points
			if contains(i, "ret "):
				blocks[currentname].append(i)
				inblock = False
				currentcounter += 1
				continue
			# the issue is their can be multiple labels per br so
			isBr = i.strip().startswith("br")
			if isBr:
				# now we can safly just match for label %LABEL
				brLabels = re.findall(r"label %(.*?)(?:\,|$)", i)
				for x in brLabels:
					connections[currentname].append(x)
				blocks[currentname].append(i)
				inblock = False
				currentcounter += 1
				continue
			if i.strip().startswith("call"):
				# this is tricky because call will result in it pointing to a new edge
				# which is its succsesorr

				# that name will be the current name with a number appended
				blocks[currentname].append(i)

			blocks[currentname].append(i)
	outputToFile(connections, functioname.strip("@"))


def main() -> None:
	parser = argparse.ArgumentParser(
		prog="llvm to graph", description="converts ll to dot notation graph"
	)
	_ = parser.add_argument("filename")
	args = parser.parse_args()
	# get the provided file
	llfile = Path("./" + args.filename)
	# open it in read mode
	with llfile.open("r") as f:
		# get the lines
		lines = f.readlines()

		# first we need to get the functions
		# then we send them to process_function
		functions: dict[str, list[str]] = {}
		infunction = False
		# keeps track if a function has started yet
		firstfunction = False
		name = ""
		for i in lines:
			if not infunction:
				define = regex_define.match(i)
				if define is not None:
					name = define.group(1)
					functions[name] = []
					functions[name].append(i)
					infunction = True
					firstfunction = True
				elif firstfunction == False:
					name = "global"
					functions[name] = []
					functions[name].append(i)

			else:
				if contains(i, "}"):
					functions[name].append(i)
					name = ""
					infunction = False
				else:
					functions[name].append(i)
		for _, functionlist in functions.items():
			process_function(functionlist)


def outputToFile(connections: dict[str, list[str]], name: str) -> None:
	outfile = Path(f"./{name}.dot")
	x = 0
	output = "digraph {\n"
	nodes: dict[str, int] = {}
	for key in connections:
		output += "		Node" + str(x) + ' [shape=record,label=""]\n'
		nodes[key] = x
		x += 1
	x = 0
	for key, value in connections.items():
		j = 0
		for i in value:
			output += (
				"		Node" + str(x) + " -> Node" + str(nodes[i]) + " [label=" + str(j) + "];\n"
			)
			j += 1
		x += 1
	output += "}"
	with outfile.open("w+") as f:
		_ = f.write(output)


if __name__ == "__main__":
	main()
