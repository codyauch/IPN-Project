import math
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


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

            bytes = re.compile("(?: length: )(.*?(?= ))").search(line).group(1)

            processed_data.append([type, time, node, interface, bytes, id])

        except Exception as e:
            print("exception encountered")
            print(line)
            print(e)

    
    df = pd.DataFrame(processed_data, columns=["type", "time", "node1", "interface", "bytes", "id"])
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
    
    df = df[["node1", "interface", "node2", "type", "time", "bytes", "id"]]

    df = df.drop_duplicates()

    # need to merge the df to itself, need to join them together

    df_queue = df[df["type"] == "+"]
    df_dequeue = df[df["type"] == "-"]
    df_type = df[df["type"] == "r"]

    df = df_queue.merge(df_dequeue, how="left", on="id")
    df = df.merge(df_type, how="left", on="id")

    print(df)

    df[["node_sending", "node_receiving", "interface", "time_queued", "time_dequeued", "time_received", "bytes", "id"]] = df[["node1_x", "node2_x", "interface_x", "time_x", "time_y", "time", "bytes_x", "id"]]

    df = df[["node_sending", "node_receiving", "interface", "time_queued", "time_dequeued", "time_received", "bytes", "id"]]

    return df


def expand_dataframe(df):
    # columns: "node_sending", "node_receiving", "interface", "time_queued", "time_dequeued", "time_received", "id"

    df[["time_queued", "time_dequeued", "time_received"]] = df[["time_queued", "time_dequeued", "time_received"]].astype(float)

    # calculate time from being queued to received
    df["total_package_time"] = df["time_received"] - df["time_queued"]

    # calculate time being queued
    df["time_queued"] = df["time_dequeued"] - df["time_queued"]

    # calculate the message time in transit
    df["total_time"] = df["time_received"] -  df["time_dequeued"]

    return df


def calculate_statistics(df):
    print("Average time from being queued to received")
    print(df["total_package_time"].mean())

    print("Average time being queued")
    print(df["time_queued"].mean())

    print("Average message time in transit")
    print(df["total_time"].mean())

    # should be graphed with respect to time

    print("Average amount of data sent")
    print(df["bytes"].mean())

    # should be graphed with respect to time


def graph_stats(df):
    # graph the average message time in transit
    # get max and min time
    min = math.floor(df["time_queued"].min())
    max = math.ceil(df["time_received"].max())

    # create time splits
    # 1000 seconds time step
    time_step = np.arange(min, max, 1000)
    x = np.arange(min + 500, max - 500, 1000)

    grouped_df = df.groupby(pd.cut(df["time_dequeued"], time_step, include_lowest=True)).mean()

    print("time step", len(time_step), min, max)
    print(len(grouped_df))

    plt.plot(x, grouped_df["total_time"])
    plt.show()
    plt.clf()

    plt.plot(x, grouped_df["bytes"])
    plt.show()
    plt.clf()


def get_graphs():
    print("Create graphs")

    # try:
    df = pd.read_csv("data/message_stats.csv")
    graph_stats(df)
    # except Exception as e:
    #     print("ran into error, likely could not find file")
    #     print(e)


def get_statistics():
    print("Calculate statistics")

    try:
        df = pd.read_csv("data/message_stats.csv")
        calculate_statistics(df)
    except Exception as e:
        print("ran into error, likely could not find file")
        print(e)


def save_dataframe():
    print("Saving statistical data")

    df = create_stats_df()
    df = expand_dataframe(df)

    df.to_csv("data/message_stats.csv")


# for testing
# save_dataframe()
get_graphs()
