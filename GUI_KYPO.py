import yaml
import os
import tkinter as tk
from tkinter import ttk, messagebox


def generate_topology(name, hosts, routers, networks, net_mappings, router_mappings, groups):
    topology = {
        'name': name,
        'hosts': hosts,
        'routers': routers,
        'networks': networks,
        'net_mappings': net_mappings,
        'router_mappings': router_mappings,
        'groups': [{'name': group['name'], 'nodes': group['hosts']} for group in groups] if groups else []
    }
    return yaml.dump(topology, sort_keys=False)


def create_directories(base_dir, hosts):
    provisioning_dir = os.path.join(base_dir, 'provisioning')
    roles_dir = os.path.join(provisioning_dir, 'roles')

    os.makedirs(roles_dir, exist_ok=True)

    for host in hosts:
        host_dir = os.path.join(roles_dir, host['name'])
        os.makedirs(host_dir, exist_ok=True)

        for sub_dir in ['files', 'tasks', 'vars']:
            os.makedirs(os.path.join(host_dir, sub_dir), exist_ok=True)


import os


def save_requirements(base_dir):
    requirements_content = """- name: disable-qxl
  src: https://gitlab.ics.muni.cz/muni-kypo/ansible-roles/disable-qxl.git
  scm: git
  version: 1.0.0

- name: sandbox-logging-bash
  src: https://gitlab.ics.muni.cz/muni-kypo/ansible-roles/sandbox-logging-bash.git
  scm: git
  version: 1.0.1

- name: sandbox-logging-forward
  src: https://gitlab.ics.muni.cz/muni-kypo/ansible-roles/sandbox-logging-forward.git
  scm: git
  version: 1.0.1

- name: kypo-user-access
  src: https://gitlab.ics.muni.cz/muni-kypo-crp/backend-python/ansible-networking-stage/kypo-user-access.git
  scm: git
  version: 1.0.0

- name: hosts-aliases
  src: https://gitlab.ics.muni.cz/muni-kypo/ansible-roles/hosts-aliases.git
  scm: git
  version: 1.0.0
"""
    provisioning_dir = os.path.join(base_dir, 'provisioning')
    os.makedirs(provisioning_dir, exist_ok=True)
    requirements_file = os.path.join(provisioning_dir, 'requirements.yml')

    with open(requirements_file, 'w') as file:
        file.write(requirements_content)


def save_topology(name, hosts, routers, networks, net_mappings, router_mappings, groups):
    topology_yaml = generate_topology(name, hosts, routers, networks, net_mappings, router_mappings, groups)
    base_dir = os.path.join(os.getcwd(), name)
    os.makedirs(base_dir, exist_ok=True)

    output_file = os.path.join(base_dir, "topology.yml")
    with open(output_file, 'w') as file:
        file.write(topology_yaml)

    create_directories(base_dir, hosts)
    save_requirements(base_dir)
    return output_file


class TopologyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CYBERCOR Topology Generator")
        self.root.geometry("1920x1080")
        self.root.configure(background="#00304E")
        self.name = tk.StringVar()
        self.available_images = [
            "Win10_x86-64", "alpine", "cirros", "debian", "debian-10", "debian-10-x86_64", "debian-11",
            "debian-11-man", "debian-11-x86_64", "debian-12.7", "debian-9-x86_64", "kali", "ubuntu-focal-x86_64",
            "xubuntu-18.04", "debian-11-man-preinstalled", "centos-7.9", "cirros-0-x86_64", "debian-9-x86_64",
            "debian-10-x86_64", "kali-2020.4", "ubuntu-bionic-x86_64", "windows-10", "windows-server-2019"
        ]
        self.available_flavors = ["csirtmu.tiny1x4", "csirtmu.tiny1x2", "csirtmu.small2x4", "csirtmu.small2x8",
                                  "csirtmu.medium4x8", "csirtmu.medium4x16", "csirtmu.large8x16", "csirtmu.large8x32",
                                  "csirtmu.jumbo16x32", "csirtmu.jumbo16x64", "standard.small"]
        self.available_users = ["debian", "windows", "ubuntu", "cirros", "centos"]
        self.hosts = []
        self.routers = []
        self.networks = []
        self.net_mappings = []
        self.router_mappings = []
        self.groups = []

        self.create_widgets()

    def create_widgets(self):

        style = ttk.Style()
        style.theme_use("default")  # Use the default ttk theme
        style.configure(
            "CustomCombobox.TCombobox",
            fieldbackground="#333333",  # Dark background for the field
            background="#444444",  # Dropdown background
            foreground="white",  # White text
            selectforeground="white",  # White text when selected
            selectbackground="#555555",  # Slightly darker selection background
        )
        style.map(
            "CustomCombobox.TCombobox",
            fieldbackground=[("readonly", "#333333")],
            background=[("readonly", "#444444")],
            foreground=[("readonly", "white")],
            selectforeground=[("readonly", "white")],
            selectbackground=[("readonly", "#555555")],
        )

        tk.Label(
            self.root, text="CYBERCOR Topology Generator",
            font=("Helvetica", 16, "bold"), bg="#00304E", fg="#39FF14", pady=10
        ).grid(row=0, column=5, columnspan=10, sticky="ew")

        # Topology Name
        tk.Label(self.root, text="Topology Name:", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=1,
                                                                                                            column=0,
                                                                                                            sticky="w",
                                                                                                            padx=10,
                                                                                                            pady=5)
        tk.Entry(self.root, textvariable=self.name, font=("Helvetica", 12), width=30, bg="#333333", fg="white",
                 insertbackground="white").grid(row=1, column=1, columnspan=3, sticky="ew", padx=10, pady=5)

        # Host Section
        tk.Label(self.root, text="Add Host", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=2, column=0,
                                                                                                      sticky="w",
                                                                                                      padx=10, pady=5)
        self.host_name = tk.StringVar()
        self.host_image = tk.StringVar(value=self.available_images[0])
        self.host_flavor = tk.StringVar(value=self.available_flavors[0])
        self.host_user = tk.StringVar(value=self.available_users[0])
        self.host_hidden = tk.BooleanVar(value=False)

        tk.Label(self.root, text="Host Name", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=3, column=0)
        tk.Entry(self.root, textvariable=self.host_name, width=15, bg="#333333", fg="white",
                 insertbackground="white").grid(row=3, column=1, padx=5, pady=5)

        tk.Label(self.root, text="Image", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=3, column=2)
        ttk.Combobox(self.root, values=self.available_images, textvariable=self.host_image, width=15,
                     style="CustomCombobox.TCombobox").grid(row=3,
                                                            column=3,
                                                            padx=5,
                                                            pady=5)

        tk.Label(self.root, text="Flavor", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=3, column=4)
        ttk.Combobox(self.root, values=self.available_flavors, textvariable=self.host_flavor, width=15,
                     style="CustomCombobox.TCombobox").grid(row=3,
                                                            column=5,
                                                            padx=5,
                                                            pady=5)

        tk.Label(self.root, text="Management User", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=3,
                                                                                                             column=6)
        ttk.Combobox(self.root, values=self.available_users, textvariable=self.host_user, width=15,
                     style="CustomCombobox.TCombobox").grid(row=3,
                                                            column=7,
                                                            padx=5, pady=5)

        tk.Checkbutton(self.root, text="Hidden", variable=self.host_hidden, bg="#214f07", fg="black",
                       activebackground="#39FF14", activeforeground="black").grid(row=3, column=8, padx=5, pady=5)
        tk.Button(self.root, text="Add Host", command=self.add_host, bg="#214f07", fg="white",
                  activebackground="#39FF14", activeforeground="white").grid(row=3, column=9, padx=5, pady=5)

        # Router Section
        tk.Label(self.root, text="Add Router", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=4, column=0,
                                                                                                        sticky="w",
                                                                                                        padx=10, pady=5)
        self.router_name = tk.StringVar()
        self.router_image = tk.StringVar(value=self.available_images[0])
        self.router_flavor = tk.StringVar(value=self.available_flavors[0])
        self.router_user = tk.StringVar(value=self.available_users[0])

        tk.Label(self.root, text="Router Name", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=5,
                                                                                                         column=0)
        tk.Entry(self.root, textvariable=self.router_name, width=15, bg="#333333", fg="white",
                 insertbackground="white").grid(row=5, column=1, padx=5, pady=5)

        tk.Label(self.root, text="Image", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=5, column=2)
        ttk.Combobox(self.root, values=self.available_images, textvariable=self.router_image, width=15,
                     style="CustomCombobox.TCombobox").grid(row=5,
                                                            column=3,
                                                            padx=5,
                                                            pady=5)

        tk.Label(self.root, text="Flavor", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=5, column=4)
        ttk.Combobox(self.root, values=self.available_flavors, textvariable=self.router_flavor, width=15,
                     style="CustomCombobox.TCombobox").grid(row=5,
                                                            column=5,
                                                            padx=5,
                                                            pady=5)

        tk.Label(self.root, text="Management User", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=5,
                                                                                                             column=6)
        ttk.Combobox(self.root, values=self.available_users, textvariable=self.router_user, width=15,
                     style="CustomCombobox.TCombobox").grid(row=5,
                                                            column=7,
                                                            padx=5,
                                                            pady=5)

        tk.Button(self.root, text="Add Router", command=self.add_router, bg="#214f07", fg="white",
                  activebackground="#39FF14", activeforeground="white").grid(row=5, column=8, padx=5, pady=5)

        # Network Section
        tk.Label(self.root, text="Add Network", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=6,
                                                                                                         column=0,
                                                                                                         sticky="w",
                                                                                                         padx=10,
                                                                                                         pady=5)
        self.network_name = tk.StringVar()
        self.network_cidr = tk.StringVar()
        self.network_accessible = tk.BooleanVar(value=False)

        tk.Label(self.root, text="Network Name", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=7,
                                                                                                          column=0)
        tk.Entry(self.root, textvariable=self.network_name, width=15, bg="#333333", fg="white",
                 insertbackground="white").grid(row=7, column=1, padx=5, pady=5)
        tk.Label(self.root, text="CIDR", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=7, column=2)
        tk.Entry(self.root, textvariable=self.network_cidr, width=15, bg="#333333", fg="white",
                 insertbackground="white").grid(row=7, column=3, padx=5, pady=5)
        tk.Checkbutton(self.root, text="Accessible", variable=self.network_accessible, bg="#214f07", fg="black",
                       activebackground="#39FF14", activeforeground="black").grid(row=7, column=4, padx=5,
                                                                                  pady=5)
        tk.Button(self.root, text="Add Network", command=self.add_network, bg="#214f07", fg="white",
                  activebackground="#39FF14", activeforeground="white").grid(row=7, column=5, padx=5, pady=5)

        # Network Mapping Section
        tk.Label(self.root, text="Add Network Mapping", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=8,
                                                                                                                 column=0,
                                                                                                                 sticky="w",
                                                                                                                 padx=10,
                                                                                                                 pady=5)
        self.net_host = tk.StringVar()
        self.net_network = tk.StringVar()
        self.net_last_octet = tk.StringVar()

        tk.Label(self.root, text="Host", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=9, column=0)
        self.net_host_dropdown = ttk.Combobox(self.root, textvariable=self.net_host, values=[], width=15,
                                              style="CustomCombobox.TCombobox")
        self.net_host_dropdown.grid(row=9, column=1, padx=5, pady=5)

        tk.Label(self.root, text="Network", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=9, column=2)
        self.net_network_dropdown = ttk.Combobox(self.root, textvariable=self.net_network, values=[], width=15,
                                                 style="CustomCombobox.TCombobox")
        self.net_network_dropdown.grid(row=9, column=3, padx=5, pady=5)

        tk.Label(self.root, text="Last Octet", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=9, column=4)
        tk.Entry(self.root, textvariable=self.net_last_octet, width=15, bg="#333333", fg="white",
                 insertbackground="white").grid(row=9, column=5, padx=5, pady=5)

        tk.Button(self.root, text="Add Network Mapping", command=self.add_network_mapping, bg="#214f07", fg="white",
                  activebackground="#39FF14", activeforeground="white").grid(row=9, column=6, padx=5,
                                                                             pady=5)

        # Router Mapping Section
        tk.Label(self.root, text="Add Router Mapping", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=10,
                                                                                                                column=0,
                                                                                                                sticky="w",
                                                                                                                padx=10,
                                                                                                                pady=5)
        self.router_host = tk.StringVar()
        self.router_network = tk.StringVar()

        tk.Label(self.root, text="Router", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=11, column=0)
        self.router_host_dropdown = ttk.Combobox(self.root, textvariable=self.router_host, values=[], width=15,
                                                 style="CustomCombobox.TCombobox")
        self.router_host_dropdown.grid(row=11, column=1, padx=5, pady=5)

        tk.Label(self.root, text="Network", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=11, column=2)
        self.router_network_dropdown = ttk.Combobox(self.root, textvariable=self.router_network, values=[], width=15,
                                                    style="CustomCombobox.TCombobox")
        self.router_network_dropdown.grid(row=11, column=3, padx=5, pady=5)

        tk.Button(self.root, text="Add Router Mapping", command=self.add_router_mapping, bg="#214f07", fg="white",
                  activebackground="#39FF14", activeforeground="white").grid(row=11, column=4, padx=5,
                                                                             pady=5)

        tk.Label(self.root, text="Add Group", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=12, column=0,
                                                                                                       sticky="w",
                                                                                                       padx=10, pady=5)
        self.group_name = tk.StringVar()
        tk.Label(self.root, text="Group Name", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=13,
                                                                                                        column=0)
        tk.Entry(self.root, textvariable=self.group_name, width=15, bg="#333333", fg="white",
                 insertbackground="white").grid(row=13, column=1, padx=5, pady=5)

        tk.Label(self.root, text="Select Hosts", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=13,
                                                                                                          column=2)
        self.hosts_select = tk.Listbox(self.root, selectmode=tk.MULTIPLE, bg="#333333", fg="white", height=3, width=30)
        self.hosts_select.grid(row=13, column=3, padx=5, pady=5)
        for host in self.hosts:
            self.hosts_select.insert(tk.END, host["name"])

        tk.Button(self.root, text="Add Group", command=self.add_groups, bg="#214f07", fg="white",
                  activebackground="#39FF14",
                  activeforeground="white").grid(row=13, column=4, padx=5, pady=5)

        # Generate Topology
        tk.Button(self.root, text="Generate Topology", command=self.generate_topology, bg="#214f07", fg="white",
                  activebackground="#39FF14", activeforeground="white").grid(
            row=16, column=0, columnspan=7, sticky="ew", padx=12, pady=10
        )

        # Hosts Listbox with Scrollbar
        tk.Label(self.root, text="Hosts Added:", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=17,
                                                                                                          column=0,
                                                                                                          sticky="w",
                                                                                                          padx=10,
                                                                                                          pady=5)
        self.hosts_list = tk.Listbox(self.root, height=2, state="normal", bg="#333333", fg="white",
                                     selectbackground="#444444", selectforeground="white")
        self.hosts_list.grid(row=18, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        hosts_scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.hosts_list.yview)
        hosts_scrollbar.grid(row=18, column=2, sticky="ns")
        self.hosts_list.config(yscrollcommand=hosts_scrollbar.set)

        # Routers Listbox with Scrollbar
        tk.Label(self.root, text="Routers Added:", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=19,
                                                                                                            column=0,
                                                                                                            sticky="w",
                                                                                                            padx=10,
                                                                                                            pady=5)
        self.routers_list = tk.Listbox(self.root, height=2, state="normal", bg="#333333", fg="white",
                                       selectbackground="#444444", selectforeground="white")
        self.routers_list.grid(row=20, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        routers_scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.routers_list.yview)
        routers_scrollbar.grid(row=20, column=2, sticky="ns")
        self.routers_list.config(yscrollcommand=routers_scrollbar.set)

        # Networks Listbox with Scrollbar
        tk.Label(self.root, text="Networks Added:", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=21,
                                                                                                             column=0,
                                                                                                             sticky="w",
                                                                                                             padx=10,
                                                                                                             pady=5)
        self.networks_list = tk.Listbox(self.root, height=2, state="normal", bg="#333333", fg="white",
                                        selectbackground="#444444", selectforeground="white")
        self.networks_list.grid(row=22, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        networks_scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.networks_list.yview)
        networks_scrollbar.grid(row=22, column=2, sticky="ns")
        self.networks_list.config(yscrollcommand=networks_scrollbar.set)

        # Network Mappings Listbox with Scrollbar
        tk.Label(self.root, text="Network Mappings:", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=17,
                                                                                                               column=4,
                                                                                                               sticky="w",
                                                                                                               padx=10,
                                                                                                               pady=5)
        self.network_mappings_list = tk.Listbox(self.root, height=2, width=50, state="normal", bg="#333333", fg="white",
                                                selectbackground="#444444", selectforeground="white")
        self.network_mappings_list.grid(row=18, column=4, columnspan=2, sticky="nsew", padx=10, pady=5)
        network_mappings_scrollbar = tk.Scrollbar(self.root, orient="vertical",
                                                  command=self.network_mappings_list.yview)
        network_mappings_scrollbar.grid(row=18, column=6, sticky="ns")
        self.network_mappings_list.config(yscrollcommand=network_mappings_scrollbar.set)

        # Router Mappings Listbox with Scrollbar
        tk.Label(self.root, text="Router Mappings:", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=19,
                                                                                                              column=4,
                                                                                                              sticky="w",
                                                                                                              padx=10,
                                                                                                              pady=5)
        self.router_mappings_list = tk.Listbox(self.root, height=2, width=50, state="normal", bg="#333333", fg="white",
                                               selectbackground="#444444", selectforeground="white")
        self.router_mappings_list.grid(row=20, column=4, columnspan=2, sticky="nsew", padx=10, pady=5)
        router_mappings_scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.router_mappings_list.yview)
        router_mappings_scrollbar.grid(row=20, column=6, sticky="ns")
        self.router_mappings_list.config(yscrollcommand=router_mappings_scrollbar.set)

        # Groups Listbox with Scrollbar
        tk.Label(self.root, text="Groups Added:", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=21,
                                                                                                           column=4,
                                                                                                           sticky="w",
                                                                                                           padx=10,
                                                                                                           pady=5)
        self.groups_list = tk.Listbox(self.root, height=2, state="normal", bg="#333333", fg="white",
                                      selectbackground="#444444", selectforeground="white")
        self.groups_list.grid(row=22, column=4, columnspan=2, sticky="nsew", padx=10, pady=5)
        groups_scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.groups_list.yview)
        groups_scrollbar.grid(row=22, column=6, sticky="ns")
        self.groups_list.config(yscrollcommand=groups_scrollbar.set)

        # Footer
        tk.Label(
            self.root, text="Made by Gabriel Tabacaru for CYBERCOR © 2025",
            font=("Helvetica", 10), bg="#007acc", fg="white", pady=10
        ).grid(row=23, column=5, columnspan=10, sticky="ew")

    def add_host(self):
        host = {
            "name": self.host_name.get(),
            "base_box": {"image": self.host_image.get(), "man_user": self.host_user.get()},
            "flavor": self.host_flavor.get(),
            "hidden": self.host_hidden.get()
        }
        self.hosts.append(host)
        self.hosts_list.insert(tk.END, f"Host: {host['name']}, Image: {host['base_box']['image']}")
        self.hosts_select.insert(tk.END, host["name"])
        self.refresh_dropdowns()
        # Refresh host inputs
        self.host_name.set("")
        self.host_image.set(self.available_images[0])
        self.host_flavor.set(self.available_flavors[0])
        self.host_user.set(self.available_users[0])
        self.host_hidden.set(False)

    def add_router(self):
        router = {
            "name": self.router_name.get(),
            "base_box": {"image": self.router_image.get(), "man_user": self.router_user.get()},
            "flavor": self.router_flavor.get()
        }
        self.routers.append(router)
        self.routers_list.insert(tk.END, f"Router: {router['name']}, Image: {router['base_box']['image']}")
        self.refresh_dropdowns()
        # Refresh router inputs
        self.router_name.set("")
        self.router_image.set(self.available_images[0])
        self.router_flavor.set(self.available_flavors[0])
        self.router_user.set(self.available_users[0])

    def add_network(self):
        network = {
            "name": self.network_name.get(),
            "cidr": self.network_cidr.get(),
            "accessible_by_user": self.network_accessible.get()
        }
        self.networks.append(network)
        self.networks_list.insert(tk.END, f"Network: {network['name']}, CIDR: {network['cidr']}")
        self.refresh_dropdowns()

        # Refresh network inputs
        self.network_name.set("")
        self.network_cidr.set("")
        self.network_accessible.set(True)

    def add_network_mapping(self):
        if not self.hosts or not self.networks:
            messagebox.showerror("Error", "Add hosts and networks first!")
            return
        host_name = self.net_host.get()
        network_name = self.net_network.get()
        last_octet = self.net_last_octet.get()

        selected_network = next((n for n in self.networks if n["name"] == network_name), None)
        if not selected_network:
            messagebox.showerror("Error", "Invalid network selected!")
            return

        cidr_prefix = ".".join(selected_network["cidr"].split(".")[:3])
        ip = f"{cidr_prefix}.{last_octet}"
        mapping = {"host": host_name, "network": network_name, "ip": ip}
        self.net_mappings.append(mapping)
        self.network_mappings_list.insert(
            tk.END,
            f"Host: {host_name} -> Network: {network_name} (IP: {ip})"
        )
        # Refresh network mapping inputs
        self.net_host.set("")
        self.net_network.set("")
        self.net_last_octet.set("")

    def add_router_mapping(self):
        if not self.routers or not self.networks:
            messagebox.showerror("Error", "Add routers and networks first!")
            return
        router_name = self.router_host.get()
        network_name = self.router_network.get()

        selected_network = next((n for n in self.networks if n["name"] == network_name), None)
        if not selected_network:
            messagebox.showerror("Error", "Invalid network selected!")
            return

        cidr_prefix = ".".join(selected_network["cidr"].split(".")[:3])
        ip = f"{cidr_prefix}.1"
        mapping = {"router": router_name, "network": network_name, "ip": ip}
        self.router_mappings.append(mapping)
        self.router_mappings_list.insert(
            tk.END,
            f"Router: {router_name} -> Network: {network_name} (IP: {ip})"
        )
        # Refresh router mapping inputs
        self.router_host.set("")
        self.router_network.set("")

    def add_groups(self):
        group_name = self.group_name.get()
        selected_indices = self.hosts_select.curselection()
        selected_hosts = [self.hosts_select.get(i) for i in selected_indices]

        if not group_name:
            messagebox.showerror("Error", "Group name cannot be empty!")
            return

        if not selected_hosts:
            messagebox.showerror("Error", "No hosts selected to add to the group!")
            return

        group = {
            "name": group_name,
            "hosts": selected_hosts
        }
        self.groups.append(group)
        self.groups_list.insert(tk.END, f"Group: {group_name}, Hosts: {', '.join(selected_hosts)}")

        # Clear inputs
        self.group_name.set("")
        self.hosts_select.selection_clear(0, tk.END)

    def refresh_dropdowns(self):
        self.net_host_dropdown["values"] = [host["name"] for host in self.hosts]
        self.net_network_dropdown["values"] = [net["name"] for net in self.networks]
        self.router_host_dropdown["values"] = [router["name"] for router in self.routers]
        self.router_network_dropdown["values"] = [net["name"] for net in self.networks]

    def generate_topology(self):
        if not self.name.get():
            messagebox.showerror("Error", "Topology name cannot be empty!")
            return
        output_file = save_topology(self.name.get(), self.hosts, self.routers, self.networks, self.net_mappings,
                                    self.router_mappings, self.groups)
        messagebox.showinfo("Success", f"Topology saved at: {output_file}")


if __name__ == "__main__":
    root = tk.Tk()
    app = TopologyApp(root)
    root.mainloop()
