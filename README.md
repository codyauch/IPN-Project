# IPN Project

## Generating Traces

### x86

To run the simulator, install `ns-3`, `numpy`, `matplotlib`, and `pandas` with `pip` and then run
`python3 network_sim.py <protocol>`. Note that this project must be run on Linux.

### ARM

`ns-3` does not have a PyPI package on the ARM
platform. If you are using such a device, you can do the following to build and
run using Linux. (`ns-3`'s Python bindings do not support Apple Silicon, but
will work in a Linux Virtual Machine running on ARM):

```sh
# clone ns-3
git clone git@gitlab.com:nsnam/ns-3-dev.git
cd ns-3-dev

# build ns-3 with python bindings
./ns3 configure --enable-examples --enable-tests --enable-python-bindings
./ns3 build

# clone this project
cd scratch
git clone git@github.com:codyauch/IPN-Project.git
cd ..

# run the simulator
./ns3 run scratch/IPN-Project/network_sim.py -- <protocol>
```

## Running analysis

A file will generated called `network_sim.tr` in the previous step. Run
`python3 process_data.py network_sim.tr` to get graphs and stats on that
data.

## Results

Each protocol was run for one hour (3600 seconds) at 1 Mbps being transmitted.

| Protocol | Send (bytes) | Receive (bytes) | Success Rate (%) |
|---|---|---|---|
| TCP New Reno | 81754112 | 81754112 | 100 |
| TCP | 81476608 | 81476608 | 100 |
| UDP | 449874944 | 435843072 | 96.8 |

