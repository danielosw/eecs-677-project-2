import argparse
import re
from operator import contains
from pathlib import Path


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

		for i in lines:
			if not inblock:
				# regex for checking for define
				define = re.match(r"define .*? (.*?)\(", i)
				if define is not None:
					blocknames.append(define.group(1))
					inblock = True
					currentname = define.group(1)
					blocks[currentname] = []
					connections[currentname] = []

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
					continue
				blocks[currentname].append(i)
		outputToFile(connections)


def outputToFile(connections: dict[str, list[str]]) -> None:
	outfile = Path("./main.dot")
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
