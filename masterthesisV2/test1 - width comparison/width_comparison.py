import networkx as nx  # This package provides graphs.
import networkx.algorithms.approximation as app  # This package provides a tree decomposition heuristic.
import pyeda.inter as eda  # This package provides boolean expression formulas.
import os  # This package provides access to the operating system.

RESULT_FILENAME = "result.txt"  # Change here to rename the result file.

# Change the names here to change the name of the used bash scripts.
PROCESSING_SCRIPT_NAME = "processing.sh"
FLOWCUTTER_SCRIPT_NAME = "flowcutter.sh"

# Change the names here to use other directories or to change the name of the used bash scripts.
INPUT_DIRECTORY_NAME = "input"
PREPROCESSING_DIRECTORY_NAME = "preprocessing"
GRAPH_DIRECTORY_NAME = "graphs"
TREE_DECOMPOSITION_DIRECTORY_NAME = "decompositions"

# Time (in seconds) that flowcutter uses for each calculation of a tree decomposition.
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


class Node:  # The class Node is a own tree decomposition node implementation.
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

    def width(self):
        width = len(self.bag_x) + len(self.bag_c) - 1
        for child in self.children:
            child_width = child.width()
            if child_width > width:
                width = child_width
        return width


def read_qdimacs_file(basename):  # Method to read a qdimacs file at a given path.
    path_input = INPUT_DIRECTORY_NAME + "/" + basename + ".qdimacs"
    path_preprocessing = PREPROCESSING_DIRECTORY_NAME + "/" + basename + "_preprocessed.qdimacs"

    # Preprocessing the input file to achieve an improvement of the result.
    os.system("sh " + PROCESSING_SCRIPT_NAME + " " + path_input + " " + path_preprocessing)

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


def get_primalgraph(clauses):  # Build the primalgraph of a given formula.
    primalgraph = nx.Graph()
    for clause in clauses:
        clause_as_list = list(clause)
        for i in range(len(clause)):
            for j in range(i+1, len(clause)):
                primalgraph.add_edge("x_" + str(abs(clause_as_list[i])), "x_" + str(abs(clause_as_list[j])))
    return primalgraph


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


def get_networkx_tree_decomposition(graph):
    # Method that computes a tree decomposition of a given graph using the min-fill heuristic implemented in the
    # pyeda package.
    _, tree_decomposition = app.treewidth_min_fill_in(graph)
    bags = list(map(set, tree_decomposition.nodes()))
    edges = []
    for edge in tree_decomposition.edges():
        edges.append((bags.index(set(edge[0])), bags.index(set(edge[1]))))
    return bags, edges


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

    # Normalize the tree decomposition so that each node has only two children at most.
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
    formula = root.transform(clauses).to_cnf()
    width = root.width()
    return formula, width


def write_result(basename, width_pg, width_bg_nx, width_bg_fc):  # Save results in the result file.
    with open(RESULT_FILENAME, "a") as file:
        file.write("RESULTS OF " + basename + ".qdimacs:\n")
        file.write("width of primalgraph: " + str(width_pg) + "\n")
        file.write("width of networkx bipartite graph after transformation: " + str(width_bg_nx) + "\n")
        file.write("width of flowcutter bipartite graph after transformation: " + str(width_bg_fc) + "\n")
        file.write("\n")


def main():
    file = open(RESULT_FILENAME, "w")  # Clear the result file.
    file.close()

    for _, _, files in os.walk("./" + INPUT_DIRECTORY_NAME):  # Calculate results for each file in the input directory.
        for filename in files:
            split = filename.split(".")
            del split[-1]
            basename = ".".join(split)
            print("start " + filename + ".")

            # Read the qdimacs input file and build both the primalgraph and the bipartite graph.
            blocks, variables, clauses = read_qdimacs_file(basename)
            primalgraph = get_primalgraph(clauses)
            width_pg, _ = app.treewidth_min_fill_in(primalgraph)  # Calculate the width of the primalgraph.
            bipartite_graph = get_bipartite_graph(clauses)
            print("computed graphs.")

            # Get the width of a tree decomposition of the bipartite graph by using the min-fill heuristic
            # given by networkx.
            bags, edges = get_networkx_tree_decomposition(bipartite_graph)
            _, width_bg_nx = special_solving(bags, edges, clauses)
            print("computed width of bipartite graph using networkx.")

            # Get the width of a tree decomposition of the bipartite graph by using flowcutter.
            bags, edges = get_flowcutter_tree_decomposition(basename, bipartite_graph)
            _, width_bg_fc = special_solving(bags, edges, clauses)
            print("computed width of bipartite graph using flowcutter.")

            # Write results in result file.
            write_result(basename, width_pg, width_bg_nx, width_bg_fc)
            print(filename + " done.")


main()
