import argparse
import re
from operator import contains
from pathlib import Path

REGEX_LABEL = re.compile(r"label %(.*?)(?:\,|$)")
REGEX_DEFINE = re.compile(r"define .*? (.*?)\(")
REGEX_BLOCK_LABEL = re.compile(r"^\s*(.*?):")
REGEX_RETURN = re.compile(r"\bret\b")
REGEX_CALL = re.compile(r"\bcall\b")
REGEX_STORE = re.compile(r"store (?P<storetype>.*?) %(?P<storefrom>.*?), ptr %(?P<storeto>.*?)$")
REGEX_SOURCE = re.compile(r"%(?P<varname>.*?) {0,}= {0,}call .*?@(.*?)\b")
REGEX_SINK = re.compile(r"\bcall void @SINK\(.*? %(?P<varname>.*?)\)")
REGEX_LOAD = re.compile(r"%(?P<loadto>.*?)\s{0,}=\s{0,}load\s{0,}(?P<type>.*?),\s{0,}ptr %(?P<loadfrom>.*?)$")
SECRET_SOURCES: dict[str, list[str]] = {}
SINKS: dict[str, list[str]] = {}
class expression:
	expressiontype: str = ""
	regexresult: re.Match[str] |None = None
	text: str = ""
	def __init__(self, text: str, expressiontype:str, regexresult: re.Match[str] | None):
		self.expressiontype = expressiontype
		self.regexresult = regexresult
		self.text = text
class block:
	parts: list[expression] = []
	name: str = ""
	connections: list[str] = []
	referenced: list[str] = []
	setvars: list[str] = []
	def __init__(self, name:str, connections: list[str] = [], referenced: list[str] = [], setvars: list[str] = [], parts:list[expression] = [],)
		self.parts=parts 
		self.name=name
		self.connections=connections
		self.referenced=referenced
		self.setvars=setvars
def complexproccessing(connections: dict[str, list[str]], functionname: str, blocks: dict[str, block]) -> None:
	# currently we just want to do the following. starting from the first block go through each connection and check load and stores to see if we run into a sink.  
	
	# assume the first is the entry
		
def process_function(lines: list[str]) -> None:
	# STARTS BLOCK: define, LABELNAME:.
	# ENDS BLOCK: br, ret
	# jumps to block: br, call
	# step 1: go line by line, breaking into blocks
	# step 2: find jump points
	# step 3: output graph
	inblock = False
	blocknames: list[str] = []
	blocks: dict[str, block] = {}
	connections: dict[str, list[str]] = {}
	currentname = ""
	functioname = ""
	currentcounter = 1
	for i in lines:
		if i.strip().startswith(";"):
			continue
		if not inblock:
			# regex for checking for define
			define = REGEX_DEFINE.match(i)
			if define is not None:
				blocknames.append(define.group(1))
				inblock = True
				currentname = define.group(1)
				blocks[currentname] = block(currentname)
				functioname = currentname
				blocks[currentname].parts.append(expression(i,"define",define))
				continue
			labels = REGEX_BLOCK_LABEL.match(i)
			if labels is not None:
				blocknames.append(labels.group(1))
				currentname = labels.group(1)
				blocks[currentname] = block(currentname)

				blocks[currentname].parts.append(expression(i,"labels",labels))

				inblock = True
				continue
		else:
			# we are in a block
			# so look for end points
			if REGEX_RETURN.search(i):
				blocks[currentname].parts.append(expression(i,"return", None))
				inblock = False
				currentcounter = 1
				continue
			# the issue is their can be multiple labels per br so
			isBr = i.strip().startswith("br")
			if isBr:
				# now we can safly just match for label %LABEL
				brLabels = REGEX_LABEL.findall(i)
				brs = REGEX_LABEL.match(i)
				for x in brLabels:
					blocks[currentname].connections.append(x)
				blocks[currentname].parts.append(expression(i,"br",brs))
				inblock = False
				currentcounter = 1
				continue
			sink = REGEX_SINK.search(i)
			if sink:
				namer = sink.group("varname")
				SINKS[currentname].append(namer)
			if REGEX_SOURCE.search(i):
				# add the source to the secret sources list
				SECRET_SOURCES[currentname].append(REGEX_SOURCE.search(i).group("varname"))
			call = REGEX_CALL.search(i)
			if call:
				callname = currentname + str(currentcounter)
				returnname = currentname + str(currentcounter + 1)
				blocks[currentname].connections.append(callname)
				blocks[callname] = block(callname,[],[],[],[expression(i,"call",call)])
				connections[callname] = [returnname]
				blocks[returnname] = block(returnname)
				currentname = returnname
				currentcounter += 2
				continue

			blocks[currentname].parts.append(expression(i,"unknown",None))
	complexproccessing(connections, functioname.strip("@"), blocks)
	outputToFile( functioname.strip("@"), blocks)


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
				define = REGEX_DEFINE.match(i)
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


def outputToFile(
	name: str, blocks: dict[str, block]
) -> None:
	outfile = Path(f"./{name}.dot")
	x = 0
	output = "digraph {\n"
	nodes: dict[str, int] = {}
	for key in blocks:
		# this line is for testing to see what is in each block
		# label = "\\n".join(blocks[key]).replace("\n", "\\n").replace("{", "").replace("}", "")
		label = ""
		output += "		Node" + str(x) + f' [shape=record,label="{label}"]\n'
		nodes[key] = x
		x += 1
	x = 0
	for key, value in blocks.items():
		j = 0
		for i in value.connections:
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
