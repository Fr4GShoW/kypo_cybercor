import os
import shutil

import yaml
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


# ---------------------- Existing Utility Functions ---------------------- #
def generate_topology(name, hosts, routers, networks, net_mappings, router_mappings, groups):
    """
    Generate a topology dictionary and dump it to YAML.
    - If 'hidden' is False, do not include it in the YAML.
    """
    filtered_hosts = []
    for h in hosts:
        host_copy = dict(h)
        if not host_copy.get("hidden"):
            host_copy.pop("hidden", None)  # remove "hidden" if it's False
        filtered_hosts.append(host_copy)

    topology = {
        'name': name,
        'hosts': filtered_hosts,
        'routers': routers,
        'networks': networks,
        'net_mappings': net_mappings,
        'router_mappings': router_mappings,
        'groups': [
            {'name': group['name'], 'nodes': group['hosts']}
            for group in groups
        ] if groups else []
    }
    return yaml.dump(topology, sort_keys=False)


def create_directories(base_dir, hosts):
    """
    Create provisioning/roles/<host_name> subdirectories (files, tasks, vars).
    """
    provisioning_dir = os.path.join(base_dir, 'provisioning')
    roles_dir = os.path.join(provisioning_dir, 'roles')
    os.makedirs(roles_dir, exist_ok=True)

    for host in hosts:
        host_dir = os.path.join(roles_dir, host['name'])
        os.makedirs(host_dir, exist_ok=True)

        for sub_dir in ['files', 'tasks', 'vars']:
            os.makedirs(os.path.join(host_dir, sub_dir), exist_ok=True)


def save_requirements(base_dir):
    """
    Save a requirements.yml file in the provisioning folder.
    """
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
    """
    Save topology.yml under <base_dir>.
    """
    topology_yaml = generate_topology(name, hosts, routers, networks, net_mappings, router_mappings, groups)
    base_dir = os.path.join(os.getcwd(), name)
    os.makedirs(base_dir, exist_ok=True)

    output_file = os.path.join(base_dir, "topology.yml")
    with open(output_file, 'w') as file:
        file.write(topology_yaml)

    create_directories(base_dir, hosts)
    save_requirements(base_dir)
    return output_file


def save_containers(base_dir, containers, container_mappings):
    """
    Save containers.yml in <base_dir>, ensuring numeric ports (no quotes).
    """
    numeric_mappings = []
    for m in container_mappings:
        mapping_copy = dict(m)
        try:
            mapping_copy["port"] = int(mapping_copy["port"])
        except ValueError:
            pass
        numeric_mappings.append(mapping_copy)

    data = {
        "containers": containers,
        "container_mappings": numeric_mappings
    }
    containers_file = os.path.join(base_dir, "containers.yml")
    with open(containers_file, "w") as f:
        yaml.dump(data, f, sort_keys=False)
    return containers_file


# ---------------------- Main Application Class ---------------------- #
class TopologyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CYBERCOR Topology Generator")
        # 3) Maximized window:
        self.root.state("zoomed")
        self.root.configure(background="#00304E")

        # 1) Data variables
        self.name = tk.StringVar()

        self.available_images = [
            "Win10_x86-64", "alpine", "cirros", "debian", "debian-10",
            "debian-10-x86_64", "debian-11", "debian-11-man",
            "debian-11-x86_64", "debian-12.7", "debian-9-x86_64",
            "kali", "ubuntu-focal-x86_64", "xubuntu-18.04",
            "debian-11-man-preinstalled", "centos-7.9", "cirros-0-x86_64",
            "debian-9-x86_64", "debian-10-x86_64", "kali-2020.4",
            "ubuntu-bionic-x86_64", "windows-10", "windows-server-2019"
        ]
        self.available_flavors = [
            "csirtmu.medium4x8", "csirtmu.tiny1x2", "m1.large", "m1.large2",
            "m1.medium", "m1.small", "m1.tiny", "m1.xlarge",
            "m2.tiny", "standard.large", "standard.medium", "standard.small",
            "standart.xlarge"
        ]
        self.available_users = ["debian", "windows", "ubuntu", "cirros", "centos"]

        # 2) Topology data
        self.hosts = []
        self.routers = []
        self.networks = []
        self.net_mappings = []
        self.router_mappings = []
        self.groups = []

        # 3) Container data
        self.containers = []
        self.container_mappings = []

        # 4) Build UI
        self.create_scrollable_container()
        self.build_main_content()

    def create_scrollable_container(self):
        """
        A scrollable area to hold our top-level Notebook (and input widgets).
        Also bind PgUp/PgDn to scroll the canvas.
        """
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg="#00304E", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=scrollbar.set)

        # A frame inside the canvas to hold all main widgets
        self.main_frame = tk.Frame(self.canvas, bg="#00304E")
        self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")

        self.main_frame.bind("<Configure>", self.on_frame_configure)

        # 5) Scrollbar from the whole app will react with PgUp/PgDn
        self.root.bind("<Down>", lambda e: self.canvas.yview_scroll(1, "pages"))  # Page Down
        self.root.bind("<Up>", lambda e: self.canvas.yview_scroll(-1, "pages"))  # Page Up

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def build_main_content(self):
        """
        Construct the 'topology input' + 'Generate' button, plus the top-level Notebook.
        """
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "CustomCombobox.TCombobox",
            fieldbackground="#333333",
            background="#444444",
            foreground="white",
            selectforeground="white",
            selectbackground="#555555",
        )
        style.map(
            "CustomCombobox.TCombobox",
            fieldbackground=[("readonly", "#333333")],
            background=[("readonly", "#444444")],
            foreground=[("readonly", "white")],
            selectforeground=[("readonly", "white")],
            selectbackground=[("readonly", "#555555")],
        )

        # Top Title
        tk.Label(
            self.main_frame, text="CYBERCOR Topology Generator",
            font=("Helvetica", 16, "bold"),
            bg="#00304E", fg="#39FF14", pady=10
        ).pack(fill="x")

        # Topology name
        name_frame = tk.Frame(self.main_frame, bg="#00304E")
        name_frame.pack(fill="x", pady=5)
        tk.Label(
            name_frame, text="Topology Name:", font=("Helvetica", 12),
            bg="#00304E", fg="#39FF14"
        ).pack(side="left", padx=5)

        tk.Entry(
            name_frame, textvariable=self.name, font=("Helvetica", 12),
            width=30, bg="#333333", fg="white", insertbackground="white"
        ).pack(side="left", padx=5)

        # Host / Router / etc. config buttons
        self.build_add_host_section()
        self.build_add_router_section()
        self.build_add_network_section()
        self.build_add_mappings_section()
        self.build_add_groups_section()
        self.build_container_sections()

        # Generate Button
        gen_button = tk.Button(
            self.main_frame, text="Generate Topology",
            command=self.generate_topology,
            bg="#214f07", fg="white", activebackground="#39FF14",
            activeforeground="white"
        )
        gen_button.pack(fill="x", padx=10, pady=10)

    # ---------------------------------------------------------------------
    # A small helper to handle mouse wheel scrolling on listboxes
    # ---------------------------------------------------------------------
    def _on_mousewheel(self, event, widget):
        """
        For Windows: event.delta is multiples of 120. For Mac, you might need a different approach.
        """
        widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    # ---------------------------------------------------------------------
    # Below: widget builders for each section
    # ---------------------------------------------------------------------
    def build_add_host_section(self):
        sec = tk.Frame(self.main_frame, bg="#00304E")
        sec.pack(fill="x", pady=10)

        tk.Label(sec, text="Add Host", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=0, column=0,
                                                                                                sticky="w")

        self.host_name = tk.StringVar()
        self.host_image = tk.StringVar(value=self.available_images[0])
        self.host_flavor = tk.StringVar(value=self.available_flavors[0])
        self.host_user = tk.StringVar(value=self.available_users[0])
        self.host_hidden = tk.BooleanVar(value=False)
        self.host_docker = tk.BooleanVar(value=False)

        # Host Name
        tk.Label(sec, text="Host Name", bg="#00304E", fg="#39FF14").grid(row=1, column=0, sticky="w")
        tk.Entry(sec, textvariable=self.host_name, bg="#333333", fg="white", insertbackground="white").grid(row=1,
                                                                                                            column=1)

        # Image
        tk.Label(sec, text="Image", bg="#00304E", fg="#39FF14").grid(row=1, column=2, sticky="w")
        ttk.Combobox(sec, values=self.available_images, textvariable=self.host_image,
                     style="CustomCombobox.TCombobox").grid(row=1, column=3)

        # Flavor
        tk.Label(sec, text="Flavor", bg="#00304E", fg="#39FF14").grid(row=1, column=4, sticky="w")
        ttk.Combobox(sec, values=self.available_flavors, textvariable=self.host_flavor,
                     style="CustomCombobox.TCombobox").grid(row=1, column=5)

        # User
        tk.Label(sec, text="User", bg="#00304E", fg="#39FF14").grid(row=1, column=6, sticky="w")
        ttk.Combobox(sec, values=self.available_users, textvariable=self.host_user,
                     style="CustomCombobox.TCombobox").grid(row=1, column=7)

        # Hidden
        tk.Checkbutton(sec, text="Hidden", variable=self.host_hidden, bg="#00304E", fg="white",
                       selectcolor="#214f07").grid(row=1, column=8, padx=5)

        # Docker
        tk.Checkbutton(sec, text="Docker", variable=self.host_docker, bg="#00304E", fg="white",
                       selectcolor="#214f07").grid(row=1, column=9, padx=5)

        tk.Button(sec, text="Add Host", command=self.add_host, bg="#214f07", fg="white").grid(row=1, column=10, padx=5)

        # Below, a listbox to show added hosts
        tk.Label(sec, text="Hosts Added:", bg="#00304E", fg="#39FF14").grid(row=2, column=0, sticky="w", pady=(10, 0))

        # 1) Smaller listbox w/ scrollbar
        host_list_frame = tk.Frame(sec, bg="#00304E")
        host_list_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

        self.hosts_list = tk.Listbox(host_list_frame, bg="#333333", fg="white", height=4, width=60)
        self.hosts_list.pack(side="left", fill="both", expand=True)

        hosts_list_scroll = tk.Scrollbar(host_list_frame, orient="vertical", command=self.hosts_list.yview)
        hosts_list_scroll.pack(side="right", fill="y")
        self.hosts_list.configure(yscrollcommand=hosts_list_scroll.set)

        # Bind mousewheel
        self.hosts_list.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, self.hosts_list))

        # We'll use self.hosts_select in add_groups
        self.hosts_select = tk.Listbox(sec, selectmode=tk.MULTIPLE, bg="#333333", fg="white", height=2, width=30)

    def build_add_router_section(self):
        sec = tk.Frame(self.main_frame, bg="#00304E")
        sec.pack(fill="x", pady=10)

        tk.Label(sec, text="Add Router", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=0, column=0,
                                                                                                  sticky="w")

        self.router_name = tk.StringVar()
        self.router_image = tk.StringVar(value=self.available_images[0])
        self.router_flavor = tk.StringVar(value=self.available_flavors[0])
        self.router_user = tk.StringVar(value=self.available_users[0])

        tk.Label(sec, text="Router Name", bg="#00304E", fg="#39FF14").grid(row=1, column=0, sticky="w")
        tk.Entry(sec, textvariable=self.router_name, bg="#333333", fg="white").grid(row=1, column=1)

        tk.Label(sec, text="Image", bg="#00304E", fg="#39FF14").grid(row=1, column=2, sticky="w")
        ttk.Combobox(sec, values=self.available_images, textvariable=self.router_image,
                     style="CustomCombobox.TCombobox").grid(row=1, column=3)

        tk.Label(sec, text="Flavor", bg="#00304E", fg="#39FF14").grid(row=1, column=4, sticky="w")
        ttk.Combobox(sec, values=self.available_flavors, textvariable=self.router_flavor,
                     style="CustomCombobox.TCombobox").grid(row=1, column=5)

        tk.Label(sec, text="User", bg="#00304E", fg="#39FF14").grid(row=1, column=6, sticky="w")
        ttk.Combobox(sec, values=self.available_users, textvariable=self.router_user,
                     style="CustomCombobox.TCombobox").grid(row=1, column=7)

        tk.Button(sec, text="Add Router", command=self.add_router, bg="#214f07", fg="white").grid(row=1, column=8,
                                                                                                  padx=5)

        tk.Label(sec, text="Routers Added:", bg="#00304E", fg="#39FF14").grid(row=2, column=0, sticky="w", pady=(10, 0))

        router_list_frame = tk.Frame(sec, bg="#00304E")
        router_list_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

        self.routers_list = tk.Listbox(router_list_frame, bg="#333333", fg="white", height=4, width=60)
        self.routers_list.pack(side="left", fill="both", expand=True)

        routers_list_scroll = tk.Scrollbar(router_list_frame, orient="vertical", command=self.routers_list.yview)
        routers_list_scroll.pack(side="right", fill="y")
        self.routers_list.configure(yscrollcommand=routers_list_scroll.set)
        self.routers_list.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, self.routers_list))

    def build_add_network_section(self):
        sec = tk.Frame(self.main_frame, bg="#00304E")
        sec.pack(fill="x", pady=10)

        tk.Label(sec, text="Add Network", font=("Helvetica", 12), bg="#00304E", fg="#39FF14").grid(row=0, column=0,
                                                                                                   sticky="w")

        self.network_name = tk.StringVar()
        self.network_cidr = tk.StringVar()
        self.network_accessible = tk.BooleanVar(value=False)

        tk.Label(sec, text="Name", bg="#00304E", fg="#39FF14").grid(row=1, column=0, sticky="w")
        tk.Entry(sec, textvariable=self.network_name, bg="#333333", fg="white").grid(row=1, column=1)

        tk.Label(sec, text="CIDR", bg="#00304E", fg="#39FF14").grid(row=1, column=2, sticky="w")
        tk.Entry(sec, textvariable=self.network_cidr, bg="#333333", fg="white").grid(row=1, column=3)

        tk.Checkbutton(sec, text="Accessible", variable=self.network_accessible,
                       bg="#00304E", fg="white", selectcolor="#214f07").grid(row=1, column=4, padx=5)

        tk.Button(sec, text="Add Network", command=self.add_network,
                  bg="#214f07", fg="white").grid(row=1, column=5, padx=5)

        tk.Label(sec, text="Networks Added:", bg="#00304E", fg="#39FF14").grid(row=2, column=0, sticky="w",
                                                                               pady=(10, 0))

        network_list_frame = tk.Frame(sec, bg="#00304E")
        network_list_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

        self.networks_list = tk.Listbox(network_list_frame, bg="#333333", fg="white", height=4, width=60)
        self.networks_list.pack(side="left", fill="both", expand=True)

        networks_list_scroll = tk.Scrollbar(network_list_frame, orient="vertical", command=self.networks_list.yview)
        networks_list_scroll.pack(side="right", fill="y")
        self.networks_list.configure(yscrollcommand=networks_list_scroll.set)
        self.networks_list.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, self.networks_list))

    def build_add_mappings_section(self):
        sec = tk.Frame(self.main_frame, bg="#00304E")
        sec.pack(fill="x", pady=10)

        # For Network Mappings
        tk.Label(sec, text="Add Network Mapping", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=0, column=0, sticky="w")

        self.net_host = tk.StringVar()
        self.net_network = tk.StringVar()
        self.net_last_octet = tk.StringVar()

        tk.Label(sec, text="Host:", bg="#00304E", fg="#39FF14").grid(row=1, column=0, sticky="e")
        self.net_host_dropdown = ttk.Combobox(sec, textvariable=self.net_host, style="CustomCombobox.TCombobox")
        self.net_host_dropdown.grid(row=1, column=1, padx=5)

        tk.Label(sec, text="Network:", bg="#00304E", fg="#39FF14").grid(row=1, column=2, sticky="e")
        self.net_network_dropdown = ttk.Combobox(sec, textvariable=self.net_network, style="CustomCombobox.TCombobox")
        self.net_network_dropdown.grid(row=1, column=3, padx=5)

        tk.Label(sec, text="Last Octet:", bg="#00304E", fg="#39FF14").grid(row=1, column=4, sticky="e")
        tk.Entry(sec, textvariable=self.net_last_octet, bg="#333333", fg="white").grid(row=1, column=5, padx=5)

        tk.Button(sec, text="Add Mapping", command=self.add_network_mapping,
                  bg="#214f07", fg="white").grid(row=1, column=6, padx=5)

        mapping_list_frame = tk.Frame(sec, bg="#00304E")
        mapping_list_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

        self.network_mappings_list = tk.Listbox(mapping_list_frame, bg="#333333", fg="white", height=4, width=60)
        self.network_mappings_list.pack(side="left", fill="both", expand=True)

        netmap_scroll = tk.Scrollbar(mapping_list_frame, orient="vertical", command=self.network_mappings_list.yview)
        netmap_scroll.pack(side="right", fill="y")
        self.network_mappings_list.configure(yscrollcommand=netmap_scroll.set)
        self.network_mappings_list.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, self.network_mappings_list))

        # For Router Mappings
        tk.Label(sec, text="Add Router Mapping", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=3, column=0, sticky="w")

        self.router_host = tk.StringVar()
        self.router_network = tk.StringVar()

        tk.Label(sec, text="Router:", bg="#00304E", fg="#39FF14").grid(row=4, column=0, sticky="e")
        self.router_host_dropdown = ttk.Combobox(sec, textvariable=self.router_host,
                                                 style="CustomCombobox.TCombobox")
        self.router_host_dropdown.grid(row=4, column=1, padx=5)

        tk.Label(sec, text="Network:", bg="#00304E", fg="#39FF14").grid(row=4, column=2, sticky="e")
        self.router_network_dropdown = ttk.Combobox(sec, textvariable=self.router_network,
                                                    style="CustomCombobox.TCombobox")
        self.router_network_dropdown.grid(row=4, column=3, padx=5)

        tk.Button(sec, text="Add Router Mapping", command=self.add_router_mapping,
                  bg="#214f07", fg="white").grid(row=4, column=4, padx=5)

        router_list_frame = tk.Frame(sec, bg="#00304E")
        router_list_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

        self.router_mappings_list = tk.Listbox(router_list_frame, bg="#333333", fg="white", height=4, width=60)
        self.router_mappings_list.pack(side="left", fill="both", expand=True)

        routermap_scroll = tk.Scrollbar(router_list_frame, orient="vertical", command=self.router_mappings_list.yview)
        routermap_scroll.pack(side="right", fill="y")
        self.router_mappings_list.configure(yscrollcommand=routermap_scroll.set)
        self.router_mappings_list.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, self.router_mappings_list))

    def build_add_groups_section(self):
        sec = tk.Frame(self.main_frame, bg="#00304E")
        sec.pack(fill="x", pady=10)

        tk.Label(sec, text="Add Group", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=0, column=0, sticky="w", pady=5)

        self.group_name = tk.StringVar()
        tk.Label(sec, text="Group Name:", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(sec, textvariable=self.group_name, width=15,
                 bg="#333333", fg="white", insertbackground="white").grid(row=1, column=1, padx=5, pady=5)

        tk.Label(sec, text="Select Hosts:", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=1, column=2, sticky="e", padx=5, pady=5)

        hosts_select_frame = tk.Frame(sec, bg="#00304E")
        hosts_select_frame.grid(row=1, column=3, padx=5, pady=5, sticky="nsew")

        self.hosts_select = tk.Listbox(hosts_select_frame, selectmode=tk.MULTIPLE,
                                       bg="#333333", fg="white", height=4, width=30)
        self.hosts_select.pack(side="left", fill="both", expand=True)

        hosts_select_scroll = tk.Scrollbar(hosts_select_frame, orient="vertical", command=self.hosts_select.yview)
        hosts_select_scroll.pack(side="right", fill="y")
        self.hosts_select.configure(yscrollcommand=hosts_select_scroll.set)
        self.hosts_select.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, self.hosts_select))

        tk.Button(sec, text="Add Group", command=self.add_groups,
                  bg="#214f07", fg="white", activebackground="#39FF14",
                  activeforeground="white").grid(row=1, column=4, padx=5, pady=5)

        groups_list_frame = tk.Frame(sec, bg="#00304E")
        groups_list_frame.grid(row=2, column=0, columnspan=5, sticky="nsew", padx=10, pady=5)

        self.groups_list = tk.Listbox(groups_list_frame, bg="#333333", fg="white", height=4, width=60)
        self.groups_list.pack(side="left", fill="both", expand=True)

        groups_scroll = tk.Scrollbar(groups_list_frame, orient="vertical", command=self.groups_list.yview)
        groups_scroll.pack(side="right", fill="y")
        self.groups_list.configure(yscrollcommand=groups_scroll.set)
        self.groups_list.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, self.groups_list))

    def build_container_sections(self):
        sec = tk.Frame(self.main_frame, bg="#00304E")
        sec.pack(fill="x", pady=10)

        tk.Label(sec, text="Add Container", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=0, column=0, sticky="w")

        self.container_name = tk.StringVar()
        self.container_image = tk.StringVar(value=self.available_images[0])
        self.container_dockerfile = tk.StringVar()

        tk.Label(sec, text="Name:", bg="#00304E", fg="#39FF14").grid(row=1, column=0, sticky="w")
        tk.Entry(sec, textvariable=self.container_name, bg="#333333", fg="white").grid(row=1, column=1, padx=5)

        tk.Label(sec, text="Image:", bg="#00304E", fg="#39FF14").grid(row=1, column=2, sticky="w")
        ttk.Combobox(sec, values=self.available_images, textvariable=self.container_image,
                     style="CustomCombobox.TCombobox").grid(row=1, column=3, padx=5)

        tk.Label(sec, text="Dockerfile:", bg="#00304E", fg="#39FF14").grid(row=1, column=4, sticky="w")
        tk.Entry(sec, textvariable=self.container_dockerfile, bg="#333333", fg="white").grid(row=1, column=5, padx=5)

        tk.Button(sec, text="Add Container", command=self.add_container,
                  bg="#214f07", fg="white").grid(row=1, column=6, padx=5)

        containers_list_frame = tk.Frame(sec, bg="#00304E")
        containers_list_frame.grid(row=2, column=0, columnspan=7, sticky="nsew", padx=10, pady=5)

        self.containers_list = tk.Listbox(containers_list_frame, bg="#333333", fg="white", height=4, width=60)
        self.containers_list.pack(side="left", fill="both", expand=True)

        containers_scroll = tk.Scrollbar(containers_list_frame, orient="vertical", command=self.containers_list.yview)
        containers_scroll.pack(side="right", fill="y")
        self.containers_list.configure(yscrollcommand=containers_scroll.set)
        self.containers_list.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, self.containers_list))

        # Container Mappings
        tk.Label(sec, text="Add Container Mapping", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=3, column=0, sticky="w")

        self.mapping_container_var = tk.StringVar()
        self.mapping_port_var = tk.StringVar()
        self.docker_host_var = tk.StringVar()

        tk.Label(sec, text="Container:", bg="#00304E", fg="#39FF14").grid(row=4, column=0, sticky="e")
        self.mapping_container_dropdown = ttk.Combobox(sec, textvariable=self.mapping_container_var,
                                                       style="CustomCombobox.TCombobox")
        self.mapping_container_dropdown.grid(row=4, column=1, padx=5)

        tk.Label(sec, text="Docker Host:", bg="#00304E", fg="#39FF14").grid(row=4, column=2, sticky="e")
        self.docker_host_dropdown = ttk.Combobox(sec, textvariable=self.docker_host_var,
                                                 style="CustomCombobox.TCombobox")
        self.docker_host_dropdown.grid(row=4, column=3, padx=5)

        tk.Label(sec, text="Port:", bg="#00304E", fg="#39FF14").grid(row=4, column=4, sticky="e")
        tk.Entry(sec, textvariable=self.mapping_port_var, bg="#333333", fg="white", width=10).grid(row=4, column=5,
                                                                                                   padx=5)

        tk.Button(sec, text="Add Container Mapping", command=self.add_container_mapping,
                  bg="#214f07", fg="white").grid(row=4, column=6, padx=5)

        container_map_frame = tk.Frame(sec, bg="#00304E")
        container_map_frame.grid(row=5, column=0, columnspan=7, sticky="nsew", padx=10, pady=5)

        self.container_mappings_list = tk.Listbox(container_map_frame, bg="#333333", fg="white", height=4, width=60)
        self.container_mappings_list.pack(side="left", fill="both", expand=True)

        containermap_scroll = tk.Scrollbar(container_map_frame, orient="vertical",
                                           command=self.container_mappings_list.yview)
        containermap_scroll.pack(side="right", fill="y")
        self.container_mappings_list.configure(yscrollcommand=containermap_scroll.set)
        self.container_mappings_list.bind("<MouseWheel>",
                                          lambda e: self._on_mousewheel(e, self.container_mappings_list))

    # ---------------------------------------------------------------------
    # Add Host/Router/Network/Groups/Containers logic
    # ---------------------------------------------------------------------
    def add_host(self):
        host = {
            "name": self.host_name.get().strip(),
            "base_box": {
                "image": self.host_image.get().strip(),
                "man_user": self.host_user.get().strip()
            },
            "flavor": self.host_flavor.get().strip()
        }
        if self.host_hidden.get():
            host["hidden"] = True
        host["docker"] = self.host_docker.get()

        self.hosts.append(host)
        self.hosts_list.insert(tk.END, f"{host['name']} | {host['base_box']['image']}")
        self.hosts_select.insert(tk.END, host["name"])  # Update the hosts selection Listbox

        self.host_name.set("")
        self.host_image.set(self.available_images[0])
        self.host_flavor.set(self.available_flavors[0])
        self.host_user.set(self.available_users[0])
        self.host_hidden.set(False)
        self.host_docker.set(False)

        self.refresh_dropdowns()

    def add_router(self):
        router = {
            "name": self.router_name.get().strip(),
            "base_box": {
                "image": self.router_image.get().strip(),
                "man_user": self.router_user.get().strip()
            },
            "flavor": self.router_flavor.get().strip()
        }
        self.routers.append(router)
        self.routers_list.insert(tk.END, f"{router['name']} | {router['base_box']['image']}")
        self.router_name.set("")
        self.router_image.set(self.available_images[0])
        self.router_flavor.set(self.available_flavors[0])
        self.router_user.set(self.available_users[0])

        self.refresh_dropdowns()

    def add_network(self):
        network = {
            "name": self.network_name.get().strip(),
            "cidr": self.network_cidr.get().strip(),
            "accessible_by_user": self.network_accessible.get()
        }
        self.networks.append(network)
        self.networks_list.insert(tk.END, f"{network['name']} | {network['cidr']}")
        self.network_name.set("")
        self.network_cidr.set("")
        self.network_accessible.set(False)

        self.refresh_dropdowns()

    def add_network_mapping(self):
        if not self.hosts or not self.networks:
            messagebox.showerror("Error", "Add hosts/networks first!")
            return
        host_name = self.net_host.get().strip()
        network_name = self.net_network.get().strip()
        last_octet = self.net_last_octet.get().strip()
        if not (host_name and network_name and last_octet):
            return

        mapping = {
            "host": host_name,
            "network": network_name,
            "ip": f"?.?.?.{last_octet}"
        }
        # We'll refine IP calculation
        net_obj = next((n for n in self.networks if n["name"] == network_name), None)
        if net_obj and "cidr" in net_obj:
            cidr_parts = net_obj["cidr"].split(".")
            if len(cidr_parts) >= 3:
                prefix = ".".join(cidr_parts[:3])
                mapping["ip"] = f"{prefix}.{last_octet}"

        self.net_mappings.append(mapping)
        self.network_mappings_list.insert(tk.END, f"Host: {host_name} -> {network_name}, ip={mapping['ip']}")

        self.net_host.set("")
        self.net_network.set("")
        self.net_last_octet.set("")

    def add_router_mapping(self):
        if not self.routers or not self.networks:
            messagebox.showerror("Error", "Add routers/networks first!")
            return
        router_name = self.router_host.get().strip()
        network_name = self.router_network.get().strip()
        if not (router_name and network_name):
            return

        mapping = {
            "router": router_name,
            "network": network_name,
            "ip": "?.?.?.1"
        }
        net_obj = next((n for n in self.networks if n["name"] == network_name), None)
        if net_obj and "cidr" in net_obj:
            cidr_parts = net_obj["cidr"].split(".")
            if len(cidr_parts) >= 3:
                prefix = ".".join(cidr_parts[:3])
                mapping["ip"] = f"{prefix}.1"

        self.router_mappings.append(mapping)
        self.router_mappings_list.insert(tk.END, f"Router: {router_name} -> {network_name}, ip={mapping['ip']}")

        self.router_host.set("")
        self.router_network.set("")

    def add_groups(self):
        group_name = self.group_name.get().strip()
        if not group_name:
            messagebox.showerror("Error", "Group name cannot be empty!")
            return
        indices = self.hosts_select.curselection()
        if not indices:
            messagebox.showerror("Error", "No hosts selected!")
            return
        selected_hosts = [self.hosts_select.get(i) for i in indices]

        group = {
            "name": group_name,
            "hosts": selected_hosts
        }
        self.groups.append(group)
        self.groups_list.insert(tk.END, f"Group: {group_name}, hosts={', '.join(selected_hosts)}")

        self.group_name.set("")
        self.hosts_select.selection_clear(0, tk.END)

    def add_container(self):
        name = self.container_name.get().strip()
        if not name:
            messagebox.showerror("Error", "Container name cannot be empty!")
            return
        image = self.container_image.get().strip()
        dockerfile = self.container_dockerfile.get().strip()

        item = {"name": name}
        if dockerfile:
            item["dockerfile"] = dockerfile
            base_dir = os.path.join(os.getcwd(), self.name.get())
            os.makedirs(base_dir, exist_ok=True)
            dockerfile_dir = os.path.join(base_dir, dockerfile)
            os.makedirs(dockerfile_dir, exist_ok=True)
        else:
            item["image"] = image

        self.containers.append(item)
        msg = f"Container: {name} => "
        msg += (f"Dockerfile: {dockerfile}" if dockerfile else f"Image: {image}")
        self.containers_list.insert(tk.END, msg)

        self.container_name.set("")
        self.container_image.set(self.available_images[0])
        self.container_dockerfile.set("")

        self.refresh_container_dropdown()

    def add_container_mapping(self):
        container_name = self.mapping_container_var.get().strip()
        if not container_name:
            messagebox.showerror("Error", "Select a container!")
            return
        docker_host = self.docker_host_var.get().strip()
        port = self.mapping_port_var.get().strip()
        if not docker_host or not port:
            messagebox.showerror("Error", "Host or Port missing!")
            return

        mapping = {"container": container_name, "host": docker_host, "port": port}
        self.container_mappings.append(mapping)
        self.container_mappings_list.insert(tk.END, f"{container_name} -> {docker_host}:{port}")

        self.mapping_container_var.set("")
        self.docker_host_var.set("")
        self.mapping_port_var.set("")

    # ---------------------------------------------------------------------
    # Refresh / Generate
    # ---------------------------------------------------------------------
    def refresh_dropdowns(self):
        """
        Refresh host, network, router dropdowns
        """
        self.net_host_dropdown["values"] = [h["name"] for h in self.hosts]
        self.net_network_dropdown["values"] = [n["name"] for n in self.networks]
        self.router_host_dropdown["values"] = [r["name"] for r in self.routers]
        self.router_network_dropdown["values"] = [n["name"] for n in self.networks]
        self.refresh_container_dropdown()

    def refresh_container_dropdown(self):
        container_names = [c["name"] for c in self.containers]
        self.mapping_container_dropdown["values"] = container_names

        # Also update Docker host list
        docker_hosts = [h["name"] for h in self.hosts if h.get("docker")]
        self.docker_host_dropdown["values"] = docker_hosts

    def refresh_hosts_select(self):
        self.hosts_select.delete(0, tk.END)  # Clear existing entries
        for host in self.hosts:
            self.hosts_select.insert(tk.END, host["name"])  # Re-add all host names

    def generate_topology(self):
        if not self.name.get().strip():
            messagebox.showerror("Error", "Topology name cannot be empty!")
            return

        base_dir = os.path.join(os.getcwd(), self.name.get())
        topology_file = save_topology(
            self.name.get(),
            self.hosts,
            self.routers,
            self.networks,
            self.net_mappings,
            self.router_mappings,
            self.groups
        )

        containers_file = None
        if self.containers or self.container_mappings:
            containers_file = save_containers(base_dir, self.containers, self.container_mappings)

        msg = f"Topology saved at: {topology_file}"
        if containers_file:
            msg += f"\nContainers saved at: {containers_file}"
        messagebox.showinfo("Success", msg)

        self.build_top_notebook(base_dir)

    # ---------------------------------------------------------------------
    # Build the "top notebook" at the top of the whole app with your tabs:
    # ---------------------------------------------------------------------
    def build_top_notebook(self, base_dir):
        """
        Create a top-level Notebook with the tabs you require:
         - Main Folder (topology.yml, containers.yml, plus any other files/folders).
         - Dockerfiles (one tab per dockerfile folder).
         - Provisioning
         - Roles (subfolders per host).
         - Footer label
        """
        existing = getattr(self, "top_notebook", None)
        if existing:
            existing.destroy()

        self.top_notebook = ttk.Notebook(self.main_frame)
        self.top_notebook.pack(fill="both", expand=True, pady=10)

        # 1) Tab: main_folder (show base_dir contents)
        self.build_main_folder_tab(self.top_notebook, base_dir)

        # 2) Tab: dockerfile_folders
        self.build_dockerfile_tabs(self.top_notebook, base_dir)

        # 3) Tab: provisioning
        self.build_provisioning_tab(self.top_notebook, base_dir)

        # 4) Tab: roles
        self.build_roles_tab(self.top_notebook, base_dir)

        # 5) Footer label
        if getattr(self, 'footer_label', None):
            self.footer_label.destroy()
        self.footer_label = tk.Label(
            self.main_frame,
            text="Copyright Made by Gabriel Tăbăcaru for CYBERCOR",
            bg="#00304E", fg="white"
        )
        self.footer_label.pack(side='bottom', fill='x', pady=5)

    def build_main_folder_tab(self, notebook, base_dir):
        """
        A tab that shows the contents of base_dir (the 'main folder').
        Folders become sub-tabs, files are directly editable with autosave.
        """
        tab = tk.Frame(notebook, bg="#00304E")
        notebook.add(tab, text="main_folder")

        # "Upload File/Folder" button
        upload_btn = tk.Button(
            tab, text="Upload File/Folder",
            command=lambda: self.upload_file_or_folder(base_dir,
                                                       refresh_call=lambda: self.build_top_notebook(base_dir)),
            bg="#214f07", fg="white"
        )
        upload_btn.pack(anchor="w", pady=5, padx=10)

        # "Delete File/Folder" button
        delete_btn = tk.Button(
            tab, text="Delete File/Folder",
            command=lambda: self.delete_file_or_folder(base_dir,
                                                       refresh_call=lambda: self.build_top_notebook(base_dir)),
            bg="#820000", fg="white"
        )
        delete_btn.pack(anchor="w", pady=5, padx=10)

        # Build a sub-notebook to display the contents
        sub_nb = ttk.Notebook(tab)
        sub_nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.build_folder_content_tabs(sub_nb, base_dir, base_dir)

    def build_dockerfile_tabs(self, notebook, base_dir):
        """
        For each container with a dockerfile, create a sub-tab that shows that folder’s contents.
        """
        dockerfiles = []
        for c in self.containers:
            if "dockerfile" in c:
                df = c["dockerfile"]
                if df not in dockerfiles:
                    dockerfiles.append(df)
        if not dockerfiles:
            return

        docker_parent_tab = tk.Frame(notebook, bg="#00304E")
        notebook.add(docker_parent_tab, text="dockerfiles")

        docker_nb = ttk.Notebook(docker_parent_tab)
        docker_nb.pack(fill="both", expand=True, padx=10, pady=10)

        for df in dockerfiles:
            df_path = os.path.join(base_dir, df)
            if not os.path.isdir(df_path):
                continue

            df_tab = tk.Frame(docker_nb, bg="#00304E")
            docker_nb.add(df_tab, text=df)

            # "Upload File/Folder" in the dockerfile folder
            tk.Button(
                df_tab, text="Upload File/Folder",
                command=lambda p=df_path: self.upload_file_or_folder(
                    p, refresh_call=lambda: self.build_top_notebook(base_dir)
                ),
                bg="#214f07", fg="white"
            ).pack(anchor="w", pady=5, padx=10)

            # "Delete File/Folder"
            tk.Button(
                df_tab, text="Delete File/Folder",
                command=lambda p=df_path: self.delete_file_or_folder(
                    p, refresh_call=lambda: self.build_top_notebook(base_dir)
                ),
                bg="#820000", fg="white"
            ).pack(anchor="w", pady=5, padx=10)

            # Show folder contents
            sub_nb = ttk.Notebook(df_tab)
            sub_nb.pack(fill="both", expand=True, padx=10, pady=10)
            self.build_folder_content_tabs(sub_nb, df_path, base_dir)

    def build_provisioning_tab(self, notebook, base_dir):
        """
        Build a tab for 'provisioning/', enumerating its contents similarly.
        """
        provisioning_path = os.path.join(base_dir, "provisioning")
        if not os.path.isdir(provisioning_path):
            return

        tab = tk.Frame(notebook, bg="#00304E")
        notebook.add(tab, text="provisioning")

        tk.Button(
            tab, text="Upload File/Folder",
            command=lambda: self.upload_file_or_folder(
                provisioning_path, refresh_call=lambda: self.build_top_notebook(base_dir)
            ),
            bg="#214f07", fg="white"
        ).pack(anchor="w", pady=5, padx=10)

        tk.Button(
            tab, text="Delete File/Folder",
            command=lambda: self.delete_file_or_folder(
                provisioning_path, refresh_call=lambda: self.build_top_notebook(base_dir)
            ),
            bg="#820000", fg="white"
        ).pack(anchor="w", pady=5, padx=10)

        sub_nb = ttk.Notebook(tab)
        sub_nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.build_folder_content_tabs(sub_nb, provisioning_path, base_dir)

    def build_roles_tab(self, notebook, base_dir):
        """
        Tab for 'provisioning/roles', enumerating subfolders (one per host).
        """
        roles_path = os.path.join(base_dir, "provisioning", "roles")
        if not os.path.isdir(roles_path):
            return

        tab = tk.Frame(notebook, bg="#00304E")
        notebook.add(tab, text="roles")

        tk.Button(
            tab, text="Upload File/Folder",
            command=lambda: self.upload_file_or_folder(
                roles_path, refresh_call=lambda: self.build_top_notebook(base_dir)
            ),
            bg="#214f07", fg="white"
        ).pack(anchor="w", pady=5, padx=10)

        tk.Button(
            tab, text="Delete File/Folder",
            command=lambda: self.delete_file_or_folder(
                roles_path, refresh_call=lambda: self.build_top_notebook(base_dir)
            ),
            bg="#820000", fg="white"
        ).pack(anchor="w", pady=5, padx=10)

        nb = ttk.Notebook(tab)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        # Each subfolder for a host => separate tab
        items = sorted(os.listdir(roles_path))
        for item in items:
            item_path = os.path.join(roles_path, item)
            if os.path.isdir(item_path):
                host_tab = tk.Frame(nb, bg="#00304E")
                nb.add(host_tab, text=item)

                # Upload in the host tab
                tk.Button(
                    host_tab, text="Upload File/Folder",
                    command=lambda p=item_path: self.upload_file_or_folder(
                        p, refresh_call=lambda: self.build_top_notebook(base_dir)
                    ),
                    bg="#214f07", fg="white"
                ).pack(anchor="w", padx=5, pady=5)

                # Delete in the host tab
                tk.Button(
                    host_tab, text="Delete File/Folder",
                    command=lambda p=item_path: self.delete_file_or_folder(
                        p, refresh_call=lambda: self.build_top_notebook(base_dir)
                    ),
                    bg="#820000", fg="white"
                ).pack(anchor="w", padx=5, pady=5)

                sub_nb = ttk.Notebook(host_tab)
                sub_nb.pack(fill="both", expand=True, padx=10, pady=10)

                # Build content recursively
                self.build_folder_content_tabs(sub_nb, item_path, base_dir)

    # ---------------------------------------------------------------------
    # The core function to list folder contents in sub-tabs (files, subfolders).
    # ---------------------------------------------------------------------
    def build_folder_content_tabs(self, notebook, folder_path, base_dir):
        """
        Goes through folder_path, and for each file => create a text-editing tab with autosave.
        For each subfolder => create a sub-tab with an "Upload File/Folder" and "Delete File/Folder" button,
        then recursively call build_folder_content_tabs.
        """
        items = sorted(os.listdir(folder_path))
        for item in items:
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                # File => show an editor
                tab = tk.Frame(notebook, bg="#00304E")
                notebook.add(tab, text=item)

                txt = tk.Text(tab, bg="#333333", fg="white", wrap="word")
                txt.pack(fill="both", expand=True)
                try:
                    with open(item_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    txt.insert("1.0", content)
                except Exception as e:
                    txt.insert("1.0", f"Error reading file: {e}")

                # Autosave
                txt.bind("<KeyRelease>", lambda e, p=item_path, w=txt: self.autosave_file(p, w))

            elif os.path.isdir(item_path):
                # Subfolder => create a sub-tab with a sub-notebook
                folder_tab = tk.Frame(notebook, bg="#00304E")
                notebook.add(folder_tab, text=item)

                tk.Button(
                    folder_tab, text="Upload File/Folder",
                    command=lambda p=item_path: self.upload_file_or_folder(
                        p, refresh_call=lambda: self.build_top_notebook(base_dir)
                    ),
                    bg="#214f07", fg="white"
                ).pack(anchor="w", padx=5, pady=5)

                tk.Button(
                    folder_tab, text="Delete File/Folder",
                    command=lambda p=item_path: self.delete_file_or_folder(
                        p, refresh_call=lambda: self.build_top_notebook(base_dir)
                    ),
                    bg="#820000", fg="white"
                ).pack(anchor="w", padx=5, pady=5)

                sub_nb = ttk.Notebook(folder_tab)
                sub_nb.pack(fill="both", expand=True, padx=10, pady=10)

                self.build_folder_content_tabs(sub_nb, item_path, base_dir)

    # ---------------------------------------------------------------------
    # File/folder upload and autosave
    # ---------------------------------------------------------------------
    def upload_file_or_folder(self, target_folder, refresh_call=None):
        """
        Allows uploading either a file or an entire folder (recursively).
        After upload, calls a full rebuild (refresh_call).
        """
        is_folder = messagebox.askyesno(
            "Upload choice",
            "Upload folder? (Yes=Folder, No=File)"
        )
        if is_folder:
            folder_path = filedialog.askdirectory(initialdir=target_folder)
            if not folder_path:
                return
            folder_name = os.path.basename(folder_path)
            dest = os.path.join(target_folder, folder_name)
            if os.path.exists(dest):
                messagebox.showerror("Error", f"Folder '{folder_name}' already exists in:\n{target_folder}")
                return
            try:
                shutil.copytree(folder_path, dest)
                messagebox.showinfo("Success", f"Uploaded folder '{folder_name}' to {target_folder}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to upload folder: {e}")
                return
        else:
            file_path = filedialog.askopenfilename(initialdir=target_folder)
            if not file_path:
                return
            fname = os.path.basename(file_path)
            dest = os.path.join(target_folder, fname)
            if os.path.exists(dest):
                messagebox.showerror("Error", f"File '{fname}' already exists in:\n{target_folder}")
                return
            try:
                with open(file_path, "rb") as src, open(dest, "wb") as dst:
                    dst.write(src.read())
                messagebox.showinfo("Success", f"Uploaded file '{fname}' to {target_folder}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to upload file: {e}")
                return

        if callable(refresh_call):
            refresh_call()
            # --- Switch to the last tab in top_notebook, then scroll to top ---
            self.root.update_idletasks()
            tabs = self.top_notebook.tabs()
            if tabs:
                self.top_notebook.select(tabs[-1])
            # Scroll to top, so the UI appears as in the 1st photo
            self.canvas.yview_moveto(0.0)

    def delete_file_or_folder(self, target_folder, refresh_call=None):
        """
        Allows deleting either a file or an entire folder (recursively).
        We ensure the chosen path is indeed within target_folder before deleting,
        to avoid accidental deletion outside the project.
        After deletion, calls a full rebuild (refresh_call).
        """
        is_folder = messagebox.askyesno(
            "Delete choice",
            "Delete folder? (Yes=Folder, No=File)"
        )

        # Let user pick either a folder or file, but ensure it is inside target_folder
        if is_folder:
            folder_path = filedialog.askdirectory(initialdir=target_folder)
            if not folder_path:
                return

            # Convert both to absolute paths:
            folder_abs = os.path.abspath(folder_path)
            target_abs = os.path.abspath(target_folder)

            # Check if folder_abs is inside target_abs
            if not (folder_abs == target_abs or folder_abs.startswith(target_abs + os.sep)):
                messagebox.showerror("Error", "Selected folder is not inside the target directory!")
                return

            try:
                shutil.rmtree(folder_abs)
                messagebox.showinfo("Success", f"Deleted folder:\n{folder_abs}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete folder: {e}")
                return
        else:
            file_path = filedialog.askopenfilename(initialdir=target_folder)
            if not file_path:
                return

            file_abs = os.path.abspath(file_path)
            target_abs = os.path.abspath(target_folder)

            # Check if file_abs is inside target_abs
            if not (file_abs == target_abs or file_abs.startswith(target_abs + os.sep)):
                messagebox.showerror("Error", "Selected file is not inside the target directory!")
                return

            try:
                os.remove(file_abs)
                messagebox.showinfo("Success", f"Deleted file:\n{file_abs}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file: {e}")
                return

        if callable(refresh_call):
            refresh_call()
            # --- Switch to the last tab in top_notebook, then scroll to top ---
            self.root.update_idletasks()
            tabs = self.top_notebook.tabs()
            if tabs:
                self.top_notebook.select(tabs[-1])
            # Scroll to top, so the UI appears as in the 1st photo
            self.canvas.yview_moveto(0.0)

    def autosave_file(self, file_path, text_widget):
        """
        Write contents of 'text_widget' to 'file_path' on each key release.
        """
        try:
            content = text_widget.get("1.0", tk.END)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            # We could show an error, but let's keep silent or log if desired.
            pass


# ---------------------- Main ---------------------- #
if __name__ == "__main__":
    root = tk.Tk()
    app = TopologyApp(root)
    root.mainloop()
