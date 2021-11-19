import networkx as nx  # This package provides graphs.
import pyeda.inter as eda  # This package provides boolean expression formulas.
import os  # This package provides access to the operating system.

# Change the names here to use other directories or to change the name of the used bash scripts.
INPUT_DIRECTORY_NAME = "input"
OUTPUT_DIRECTORY_NAME = "input_new"
PREPROCESSING_DIRECTORY_NAME = "preprocessing"
POSTPROCESSING_DIRECTORY_NAME = "postprocessing"
GRAPH_DIRECTORY_NAME = "graphs"
TREE_DECOMPOSITION_DIRECTORY_NAME = "decompositions"
FLOWCUTTER_SCRIPT_NAME = "flowcutter.sh"
PROCESSING_SCRIPT_NAME = "processing.sh"

# Time (in seconds) that flowcutter gets for each calculation of a tree decomposition.
FLOWCUTTER_TIME = 30


class CVariable:  # The class CVariable represents a clause variable.
    def __init__(self, clause_number, node_number, clause):
        self.clause_number = clause_number
        self.node_number = node_number
        self.clause = list(clause)
        self.variables = set()
        for literal in clause:
            self.variables.add("x_" + str(abs(literal)))

    def __str__(self):
        return "c_" + str(self.clause_number) + "_" + str(self.node_number)


class Node:  # The class Node is my own tree decomposition node implementation.
    def __init__(self, number, bag, clauses, parent=None):
        self.number = number
        self.parent = parent
        self.children = []
        self.bag_x = set()  # bag_x contains every x_i variable of the bag.
        self.bag_c = set()  # bag_c contains every c_i_j variable of the bag.
        for variable in bag:  # Each variable of the given bag is inserted into the corresponding set.
            split = variable.split("_")
            if split[0] == "c":
                number = int(split[1])
                self.bag_c.add(CVariable(number, self.number, clauses[number - 1]))
            else:
                self.bag_x.add(variable)

    def is_root(self):
        return self.parent is None

    def bag(self):
        bag = set(self.bag_x)
        for variable in self.bag_c:
            bag.add(str(variable))
        return bag

    def introduced_x(self, variable):
        introduced = self.bag_x.intersection(variable.variables)
        for child in self.children:
            if child.get_variable(variable.clause_number):
                introduced.difference(child.bag_x)
        return introduced

    def get_variable(self, number):
        for variable in self.bag_c:
            if variable.clause_number == number:
                return variable
        return None

    def transform(self, formula=eda.expr(True)):
        # This is a recursive method to traverse the tree decomposition nodes in post order and build the new formula.

        # First the child nodes of the node are visited because of the post order traversal.
        for child in self.children:
            formula = child.transform(formula)

        # For each c-variable of the node a new "clause" is built, by which formula is extended.
        for variable in self.bag_c:
            expression = eda.expr(False)
            c_counter = 0
            c_save = None
            for child in self.children:
                child_variable = child.get_variable(variable.clause_number)
                if child_variable:
                    expression = expression | eda.exprvar(str(child_variable))
                    c_counter += 1
                    c_save = child_variable
            l_counter = 0
            for literal in variable.clause:
                x_var = "x_" + str(abs(literal))
                if x_var in self.introduced_x(variable):
                    l_counter += 1
                    if literal > 0:
                        expression = expression | eda.exprvar(x_var)
                    else:
                        expression = expression | (~ eda.exprvar(x_var))
            if c_counter == 1 and l_counter == 0:
                variable.node_number = c_save.node_number
            else:
                formula = formula & eda.Equal(eda.exprvar(str(variable)), expression)

        # Close a clause by closing the last clause variable positively.
        for variable in self.bag_c:
            if self.parent:
                if not self.parent.get_variable(variable.clause_number):
                    formula = formula & eda.exprvar(str(variable))
            else:
                formula = formula & eda.exprvar(str(variable))

        return formula


def processing(path_input, path_output):  # Processing a .qdimacs file can lead to an improvement of the result
    os.system("sh " + PROCESSING_SCRIPT_NAME + " " + path_input + " " + path_output)


def read_qdimacs_file(basename):  # Method to read a qdimacs file at a given path.
    path_input = INPUT_DIRECTORY_NAME + "/" + basename + ".qdimacs"
    path_preprocessing = PREPROCESSING_DIRECTORY_NAME + "/" + basename + "_preprocessed.qdimacs"

    # Preprocessing the input file to achieve an improvement of the result.
    processing(path_input, path_preprocessing)
    blocks = []
    variables = {}
    clauses = []
    with open(path_preprocessing, "r") as file:
        for line in file:
            split = line.strip().split(" ")
            if split[0] == 'c' or split[0] == 'p' or split[0] == '0':
                continue
            elif split[0] == 'e' or split[0] == 'a':
                blocks.append(split[0])
                del split[-1]
                del split[0]
                for item in split:
                    variables["x_" + item] = len(blocks)
            else:
                del split[-1]
                clause = set(map(int, split))
                clauses.append(clause)
    return blocks, variables, clauses


def get_bipartite_graph(clauses):  # Build the bipartite graph of a given formula.
    bipartite_graph = nx.Graph()
    for clause in clauses:
        for literal in clause:
            bipartite_graph.add_edge("c_" + str(clauses.index(clause) + 1), "x_" + str(abs(literal)))
    return bipartite_graph


def write_graph_to_file(path, graph):  # Method that saves a given graph in a .gr file.
    nodes = list(graph.nodes)
    edges = list(graph.edges)
    with open(path, "w") as file:
        file.write("p tw " + str(len(nodes)) + " " + str(len(edges)) + "\n")
        for edge in edges:
            file.write(str(nodes.index(edge[0]) + 1) + " " + str(nodes.index(edge[1]) + 1) + "\n")
    variable_dictionary = {}
    for node in nodes:
        variable_dictionary[nodes.index(node) + 1] = str(node)
    return variable_dictionary


def get_flowcutter_tree_decomposition(basename, graph):
    # Method that computes a tree decomposition of a given graph using flowcutter.

    # Save the graph as .gr file and use flowcutter to compute a tree decomposition saved in a .gr file.
    path_graph = GRAPH_DIRECTORY_NAME + "/" + basename + ".gr"
    path_td = TREE_DECOMPOSITION_DIRECTORY_NAME + "/" + basename + "_td.gr"
    variable_dictionary = write_graph_to_file(path_graph, graph)
    os.system("sh " + FLOWCUTTER_SCRIPT_NAME + " " + path_graph + " " + path_td + " " + str(FLOWCUTTER_TIME))

    # Read the calculated tree decomposition from file.
    bags = []
    edges = []
    with open(path_td, "r") as file:
        for line in file:
            split = line.strip().split(" ")
            if split[0] == 'c' or split[0] == 's':
                continue
            elif split[0] == 'b':
                del split[0]
                del split[0]
                bag = set()
                for item in split:
                    bag.add(variable_dictionary[int(item)])
                bags.append(bag)
            else:
                edges.append((int(split[0]) - 1, int(split[1]) - 1))
    return bags, edges


def special_solving(bags, edges, clauses):
    # Method for the new special solution approach, which computes an new equivalent formula for a given one.

    # Transfer the given tree decomposition into a own data structure using the class Node.
    nodes = []
    for i in range(len(bags)):
        nodes.append(Node(i + 1, bags[i], clauses))
    edges = list(edges)
    queue = [0]
    while queue:
        index = queue.pop()
        for edge in list(edges):
            i = -1
            if edge[1] == index:
                i = 0
            elif edge[0] == index:
                i = 1
            if i > -1:
                nodes[index].children.append(nodes[edge[i]])
                nodes[edge[i]].parent = nodes[index]
                queue.append(edge[i])
                edges.remove(edge)
    root = nodes[0]

    # Normalize the tree decomposition so that each node has only 2 children at most.
    queue = [root]
    while queue:
        node = queue.pop()
        size = len(node.children)
        if size == 3:
            clone = Node(len(nodes) + 1, node.bag(), clauses, node)
            nodes.append(clone)
            clone.children.append(node.children[0])
            node.children[0].parent = clone
            clone.children.append(node.children[1])
            node.children[1].parent = clone
            node.children = [clone, node.children[2]]
        elif size > 3:
            clone1 = Node(len(nodes) + 1, node.bag(), clauses, node)
            nodes.append(clone1)
            clone2 = Node(len(nodes) + 1, node.bag(), clauses, node)
            nodes.append(clone2)
            for child in node.children[:size // 2]:
                clone1.children.append(child)
                child.parent = clone1
            for child in node.children[size // 2:]:
                clone2.children.append(child)
                child.parent = clone2
            node.children = [clone1, clone2]
        queue.extend(node.children)

    # Using the transform method of the root to calculate the new formula and convert it into cnf.
    return root.transform(clauses).to_cnf()


def unit_propagation(formula, protected_variables):  # Unit propagation can lead to an improvement of the result
    litmap, _, clauses = formula.encode_cnf()
    unit_clauses = []
    for clause in clauses:
        clause = list(clause)
        variable = litmap[abs(clause[0])]
        if len(clause) == 1 and str(variable) not in protected_variables:
            unit_clauses.append(clause)
    if len(unit_clauses) == 0:
        return formula
    else:
        for clause in unit_clauses:
            variable = litmap[abs(clause[0])]
            if clause[0] > 0:
                formula = formula.restrict({variable: 1})
            else:
                formula = formula.restrict({variable: 0})
        return unit_propagation(formula, protected_variables)


def write_output(basename, extension, blocks, variables, formula):
    # Method to write a given new formula in a qdimacs format file.

    path_postprocessing = POSTPROCESSING_DIRECTORY_NAME + "/" + basename + "_postprocessed.qdimacs"
    path_output = OUTPUT_DIRECTORY_NAME + "/" + basename + "_" + extension + ".qdimacs"
    litmap, degree, clauses = formula.encode_cnf()
    with open(path_postprocessing, "w") as file:
        file.write("p cnf " + str(degree) + " " + str(len(clauses)) + "\n")
        new_blocks = []
        for _ in range(len(blocks)):
            new_blocks.append(set())
        for clause in clauses:
            for literal in clause:
                variable = str(litmap[abs(literal)])
                block = len(blocks)
                if variable in variables.keys():
                    block = variables[variable]
                new_blocks[block - 1].add(litmap[eda.exprvar(variable)])
        for block in new_blocks:
            line = str(blocks[new_blocks.index(block)]) + " "
            for variable in block:
                line += str(variable) + " "
            file.write(line + "0\n")
        for clause in clauses:
            line = ""
            for literal in clause:
                line += str(literal) + " "
            file.write(line + "0\n")

    # Preprocessing the input file to achieve an improvement of the result.
    processing(path_postprocessing, path_output)


def main():
    for _, _, files in os.walk("./" + INPUT_DIRECTORY_NAME):  # Calculate results for each file in the input directory.
        for filename in files:
            split = filename.split(".")
            del split[-1]
            basename = ".".join(split)
            print("start " + filename + ".")

            # Read the qdimacs input file and build the bipartite graph.
            blocks, variables, clauses = read_qdimacs_file(basename)
            graph = get_bipartite_graph(clauses)
            print("computed bipartite graph.")

            # Get a tree decomposition by using flowcutter and compute a new formula.
            bags, edges = get_flowcutter_tree_decomposition(basename, graph)
            formula = special_solving(bags, edges, clauses)
            print("computed formula.")

            # Using unit propagation to achieve an improvement.
            protected_variables = set()
            for variable in variables.keys():
                if blocks[variables[variable] - 1] == 'a':
                    protected_variables.add(variable)
            formula = unit_propagation(formula, protected_variables)
            print("computed unit propagation.")

            # Save the computed formula in a qdimacs file.
            write_output(basename, "new", blocks, variables, formula)
            print(filename + " done.")


main()
