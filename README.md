# Ellersoft virsh-monitor

This repository houses the `virsh-monitor` tool created by Ellersoft for the purpose of monitoring kvm/qemu VM's operated via the libvirt / virsh environment.

The tool lists the following resources:

1. all VMs managed by `libvirt`;
2. all NETs managed by `libvirt`;
3. all pools / storage managed by `libvirt`;

In addition, the tool has commands to start and stop each of the resources:

1. starting / stopping / destroying a VM domain ('running' and 'shut off' states);
2. starting / stopping / destroying a NET domain ('active' and 'inactive' states);
3. starting / stopping / destroying a storage pool domain ('active' and 'inactive' states);
