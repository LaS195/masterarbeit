import os  # This package provides access to the operating system.
import time  # This package provides access to the system time.

# Change the names here to use other directories or to change the name of the used bash scripts.
INPUT_DIRECTORY_NAME = "input"
NEW_INPUT_DIRECTORY_NAME = "input_new"
DYNQBF_RESULT_DIRECTORY_NAME = "dynQBF_results"
RUNTIME_MEASUREMENT_SCRIPT_NAME = "runtime_measurement.sh"
DYNQBF_SCRIPT_NAME = "dynqbf.sh"

RESULT_FILENAME = "result.txt"  # Change here to rename the result file.

N = 10  # Change here to change the iterations of the runtime measurement


def get_info(path, name):
    result = [-1, -1, -1, "ERROR"]
    with open(path, "r") as file:
        for line in file:
            split = line.strip().split(" ")
            if split[0] == 'p':
                result[0] = int(split[2])
                result[1] = int(split[3])
    path_dynqbf_result = DYNQBF_RESULT_DIRECTORY_NAME + "/" + name
    os.system("sh " + DYNQBF_SCRIPT_NAME + " " + path + " " + path_dynqbf_result)
    with open(path_dynqbf_result) as file:
        file.readline()
        result[2] = int(file.readline().strip().split(" ")[1])
        line = ""
        for line in file:
            pass
        result[3] = line.strip().split(" ")[1]
    return result


def runtime_measurement(path):
    time_start = time.time()
    os.system("sh " + RUNTIME_MEASUREMENT_SCRIPT_NAME + " " + path + " " + str(N))
    time_end = time.time()
    return (time_end - time_start)/N


def write_result(basename, info1, info2, runtime1, runtime2):
    with open(RESULT_FILENAME, "a") as file:
        file.write("RESULTS OF " + basename + ":\n")
        file.write("number of variables: " + str(info1[0]) + " - " + str(info2[0]) + "\n")
        file.write("number of clauses: " + str(info1[1]) + " - " + str(info2[1]) + "\n")
        file.write("dynQBF width: " + str(info1[2]) + " - " + str(info2[2]) + "\n")
        file.write("dynQBF result: " + info1[3] + " - " + info2[3] + "\n")
        file.write("avg. runtime original: " + str(runtime1) + " s\n")
        file.write("avg. runtime new: " + str(runtime2) + " s\n")
        file.write("\n")


def main():
    file = open(RESULT_FILENAME, "w")  # Clear the result file.
    file.close()

    for _, _, files in os.walk("./" + INPUT_DIRECTORY_NAME):
        for filename in files:
            split = filename.split(".")
            del split[-1]
            basename = ".".join(split)
            basename_new = basename + "_new"
            path1 = INPUT_DIRECTORY_NAME + "/" + basename + ".qdimacs"
            path2 = NEW_INPUT_DIRECTORY_NAME + "/" + basename_new + ".qdimacs"
            print("start " + filename + ".")

            info1 = get_info(path1, basename)
            info2 = get_info(path2, basename_new)
            print("got info.")

            runtime1 = runtime_measurement(path1)
            runtime2 = runtime_measurement(path2)
            print("got avg. runtimes.")

            write_result(basename, info1, info2, runtime1, runtime2)
            print(filename + " done.")


main()
