import re
import pandas as pd

# take trace file and turn it into a dataframe
def process_trace():
    file1 = open('network-sim.tr', 'r')
    Lines = file1.readlines()

    processed_data = []

    for line in Lines:
        try:
            TYPE_INDEX = 1
            TIME_INDEX = 2
            NODE_INDEX = 3
            INTERFACE_INDEX = 4

            res = re.compile("^([r\\+-]) ([0-9]*\.[0-9]*|[0-9]*[0-9]*) \/NodeList\/([0-9]*)\/DeviceList\/([0-9]*)").search(line)

            type = res.group(TYPE_INDEX)
            time = res.group(TIME_INDEX)
            node = res.group(NODE_INDEX)
            interface = res.group(INTERFACE_INDEX)

            id = re.compile("(?: id )(.*?(?= ))").search(line).group(1)

            processed_data.append([type, time, node, interface, id])

        except Exception as e:
            print("exception encountered")
            print(line)
            print(e)

    
    df = pd.DataFrame(processed_data, columns=["type", "time", "node1", "interface", "id"])
    return df


# based off of the trace file create a dataframe where each row is for 1 message id
# has information on the time queued, time dequeued, time received, sending and receiving nodes
def create_stats_df():
    trace_df = process_trace()
    interface_mapping_df = pd.read_csv("interface_mapping.csv")

    trace_df["node1"] = pd.to_numeric(trace_df["node1"])
    trace_df["interface"] = pd.to_numeric(trace_df["interface"])

    df = trace_df.merge(interface_mapping_df, left_on=["node1", "interface"], right_on=["Input Node", "Interface"], how="left")

    df["node2"] = df["Output Node"]
    
    df = df[["node1", "interface", "node2", "type", "time", "id"]]

    df = df.drop_duplicates()

    # need to merge the df to itself, need to join them together

    df_queue = df[df["type"] == "+"]
    df_dequeue = df[df["type"] == "-"]
    df_type = df[df["type"] == "r"]

    df = df_queue.merge(df_dequeue, how="left", on="id")
    df = df.merge(df_type, how="left", on="id")

    df[["node_sending", "node_receiving", "interface", "time_queued", "time_dequeued", "time_received", "id"]] = df[["node1", "node2", "interface", "time", "time_x", "time_y", "id"]]

    df = df[["node_sending", "node_receiving", "interface", "time_queued", "time_dequeued", "time_received", "id"]]

    return df


# for testing
# print(create_stats_df())
