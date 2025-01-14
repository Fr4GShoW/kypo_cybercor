import os
import yaml
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ---------------------- Existing Utility Functions ---------------------- #
def generate_topology(name, hosts, routers, networks, net_mappings, router_mappings, groups):
    """
    Generate a topology dictionary and dump it to YAML.
    - If 'hidden' is False, do not include it in the YAML.
    """
    # Remove "hidden": False from each host
    filtered_hosts = []
    for h in hosts:
        host_copy = dict(h)
        if not host_copy.get("hidden"):
            host_copy.pop("hidden", None)  # remove the key if it's False
        filtered_hosts.append(host_copy)

    topology = {
        'name': name,
        'hosts': filtered_hosts,
        'routers': routers,
        'networks': networks,
        'net_mappings': net_mappings,
        'router_mappings': router_mappings,
        'groups': [{'name': group['name'], 'nodes': group['hosts']} for group in groups] if groups else []
    }
    return yaml.dump(topology, sort_keys=False)

def create_directories(base_dir, hosts):
    """
    Create provisioning/roles/<host_name> subdirectories.
    """
    provisioning_dir = os.path.join(base_dir, 'provisioning')
    roles_dir = os.path.join(provisioning_dir, 'roles')
    os.makedirs(roles_dir, exist_ok=True)

    for host in hosts:
        # If 'hidden' was omitted or is False, that doesn't affect folder creation
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
    Save containers.yml in <base_dir> with numeric ports (no quotes).
    """
    # Convert port to int so YAML doesn't surround it with quotes
    numeric_mappings = []
    for m in container_mappings:
        mapping_copy = dict(m)
        # Attempt to convert to int
        try:
            mapping_copy["port"] = int(mapping_copy["port"])
        except ValueError:
            # If invalid integer, fallback to storing as string
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
        self.root.geometry("1920x1080")

        # Use the same background color you specified
        self.root.configure(background="#00304E")

        # ---------------------- Scrollable Frame Setup ---------------------- #
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, background="#00304E", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=scrollbar.set)

        # A frame that will hold all main widgets
        self.main_frame = tk.Frame(self.canvas, bg="#00304E")
        self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")

        self.main_frame.bind("<Configure>", self.on_frame_configure)

        # ---------------------- Data Variables ---------------------- #
        self.name = tk.StringVar()

        self.available_images = [
            "Win10_x86-64", "alpine", "cirros", "debian", "debian-10", "debian-10-x86_64", "debian-11",
            "debian-11-man", "debian-11-x86_64", "debian-12.7", "debian-9-x86_64", "kali", "ubuntu-focal-x86_64",
            "xubuntu-18.04", "debian-11-man-preinstalled", "centos-7.9", "cirros-0-x86_64", "debian-9-x86_64",
            "debian-10-x86_64", "kali-2020.4", "ubuntu-bionic-x86_64", "windows-10", "windows-server-2019"
        ]
        self.available_flavors = [
            "csirtmu.medium4x8", "csirtmu.tiny1x2", "m1.large", "m1.large2",
            "m1.medium", "m1.small", "m1.tiny", "m1.xlarge",
            "m2.tiny", "standard.large", "standard.medium", "standard.small",
            "standart.xlarge"
        ]
        self.available_users = ["debian", "windows", "ubuntu", "cirros", "centos"]

        # Topology data
        self.hosts = []
        self.routers = []
        self.networks = []
        self.net_mappings = []
        self.router_mappings = []
        self.groups = []

        # Container data
        self.containers = []
        self.container_mappings = []

        # A Notebook for Folders/Files
        self.files_notebook = None
        self.tabs_dict = {}  # store references to folder/file tabs

        # ---------------------- Build Widgets ---------------------- #
        self.create_widgets()

    def on_frame_configure(self, event):
        """
        Reset the scroll region to encompass the inner frame.
        """
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def create_widgets(self):
        # ---------------------- Style for Combobox ---------------------- #
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

        # ---------------------- Title ---------------------- #
        title_label = tk.Label(
            self.main_frame, text="CYBERCOR Topology Generator",
            font=("Helvetica", 16, "bold"),
            bg="#00304E", fg="#39FF14", pady=10
        )
        title_label.grid(row=0, column=5, columnspan=10, sticky="ew")

        # ---------------------- Topology Name ---------------------- #
        tk.Label(self.main_frame, text="Topology Name:", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=1, column=0, sticky="w", padx=10, pady=5)

        tk.Entry(self.main_frame, textvariable=self.name, font=("Helvetica", 12),
                 width=30, bg="#333333", fg="white", insertbackground="white"
        ).grid(row=1, column=1, columnspan=3, sticky="ew", padx=10, pady=5)

        # ---------------------- Host Section ---------------------- #
        tk.Label(self.main_frame, text="Add Host", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=2, column=0, sticky="w", padx=10, pady=5)

        self.host_name = tk.StringVar()
        self.host_image = tk.StringVar(value=self.available_images[0])
        self.host_flavor = tk.StringVar(value=self.available_flavors[0])
        self.host_user = tk.StringVar(value=self.available_users[0])
        self.host_hidden = tk.BooleanVar(value=False)
        self.host_docker = tk.BooleanVar(value=False)

        tk.Label(self.main_frame, text="Host Name", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=3, column=0)
        tk.Entry(self.main_frame, textvariable=self.host_name, width=15,
                 bg="#333333", fg="white", insertbackground="white"
        ).grid(row=3, column=1, padx=5, pady=5)

        tk.Label(self.main_frame, text="Image", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=3, column=2)
        ttk.Combobox(self.main_frame, values=self.available_images,
                     textvariable=self.host_image, width=15,
                     style="CustomCombobox.TCombobox"
        ).grid(row=3, column=3, padx=5, pady=5)

        tk.Label(self.main_frame, text="Flavor", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=3, column=4)
        ttk.Combobox(self.main_frame, values=self.available_flavors,
                     textvariable=self.host_flavor, width=15,
                     style="CustomCombobox.TCombobox"
        ).grid(row=3, column=5, padx=5, pady=5)

        tk.Label(self.main_frame, text="Management User", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=3, column=6)
        ttk.Combobox(self.main_frame, values=self.available_users,
                     textvariable=self.host_user, width=15,
                     style="CustomCombobox.TCombobox"
        ).grid(row=3, column=7, padx=5, pady=5)

        tk.Checkbutton(self.main_frame, text="Hidden", variable=self.host_hidden,
                       bg="#00304E", fg="white", selectcolor="#214f07").grid(row=3, column=8, padx=5, pady=5)

        tk.Checkbutton(self.main_frame, text="Docker", variable=self.host_docker,
                       bg="#00304E", fg="white", selectcolor="#214f07").grid(row=3, column=10, padx=5, pady=5)

        tk.Button(self.main_frame, text="Add Host", command=self.add_host,
                  bg="#214f07", fg="white", activebackground="#39FF14",
                  activeforeground="white"
        ).grid(row=3, column=9, padx=5, pady=5)

        # ---------------------- Router Section ---------------------- #
        tk.Label(self.main_frame, text="Add Router", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=4, column=0, sticky="w", padx=10, pady=5)

        self.router_name = tk.StringVar()
        self.router_image = tk.StringVar(value=self.available_images[0])
        self.router_flavor = tk.StringVar(value=self.available_flavors[0])
        self.router_user = tk.StringVar(value=self.available_users[0])

        tk.Label(self.main_frame, text="Router Name", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=5, column=0)
        tk.Entry(self.main_frame, textvariable=self.router_name, width=15,
                 bg="#333333", fg="white", insertbackground="white"
        ).grid(row=5, column=1, padx=5, pady=5)

        tk.Label(self.main_frame, text="Image", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=5, column=2)
        ttk.Combobox(self.main_frame, values=self.available_images,
                     textvariable=self.router_image, width=15,
                     style="CustomCombobox.TCombobox"
        ).grid(row=5, column=3, padx=5, pady=5)

        tk.Label(self.main_frame, text="Flavor", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=5, column=4)
        ttk.Combobox(self.main_frame, values=self.available_flavors,
                     textvariable=self.router_flavor, width=15,
                     style="CustomCombobox.TCombobox"
        ).grid(row=5, column=5, padx=5, pady=5)

        tk.Label(self.main_frame, text="Management User", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=5, column=6)
        ttk.Combobox(self.main_frame, values=self.available_users,
                     textvariable=self.router_user, width=15,
                     style="CustomCombobox.TCombobox"
        ).grid(row=5, column=7, padx=5, pady=5)

        tk.Button(self.main_frame, text="Add Router", command=self.add_router,
                  bg="#214f07", fg="white", activebackground="#39FF14",
                  activeforeground="white"
        ).grid(row=5, column=8, padx=5, pady=5)

        # ---------------------- Network Section ---------------------- #
        tk.Label(self.main_frame, text="Add Network", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=6, column=0, sticky="w", padx=10, pady=5)

        self.network_name = tk.StringVar()
        self.network_cidr = tk.StringVar()
        self.network_accessible = tk.BooleanVar(value=False)

        tk.Label(self.main_frame, text="Network Name", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=7, column=0)
        tk.Entry(self.main_frame, textvariable=self.network_name, width=15,
                 bg="#333333", fg="white", insertbackground="white"
        ).grid(row=7, column=1, padx=5, pady=5)

        tk.Label(self.main_frame, text="CIDR", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=7, column=2)
        tk.Entry(self.main_frame, textvariable=self.network_cidr, width=15,
                 bg="#333333", fg="white", insertbackground="white"
        ).grid(row=7, column=3, padx=5, pady=5)

        tk.Checkbutton(self.main_frame, text="Accessible", variable=self.network_accessible,
                       bg="#00304E", fg="white", selectcolor="#214f07").grid(row=7, column=4, padx=5, pady=5)

        tk.Button(self.main_frame, text="Add Network", command=self.add_network,
                  bg="#214f07", fg="white", activebackground="#39FF14",
                  activeforeground="white"
        ).grid(row=7, column=5, padx=5, pady=5)

        # ---------------------- Network Mapping Section ---------------------- #
        tk.Label(self.main_frame, text="Add Network Mapping", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=8, column=0, sticky="w", padx=10, pady=5)

        self.net_host = tk.StringVar()
        self.net_network = tk.StringVar()
        self.net_last_octet = tk.StringVar()

        tk.Label(self.main_frame, text="Host", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=9, column=0)
        self.net_host_dropdown = ttk.Combobox(self.main_frame, textvariable=self.net_host,
                                              values=[], width=15, style="CustomCombobox.TCombobox")
        self.net_host_dropdown.grid(row=9, column=1, padx=5, pady=5)

        tk.Label(self.main_frame, text="Network", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=9, column=2)
        self.net_network_dropdown = ttk.Combobox(self.main_frame, textvariable=self.net_network,
                                                 values=[], width=15, style="CustomCombobox.TCombobox")
        self.net_network_dropdown.grid(row=9, column=3, padx=5, pady=5)

        tk.Label(self.main_frame, text="Last Octet", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=9, column=4)
        tk.Entry(self.main_frame, textvariable=self.net_last_octet, width=15,
                 bg="#333333", fg="white", insertbackground="white"
        ).grid(row=9, column=5, padx=5, pady=5)

        tk.Button(self.main_frame, text="Add Network Mapping",
                  command=self.add_network_mapping,
                  bg="#214f07", fg="white", activebackground="#39FF14",
                  activeforeground="white"
        ).grid(row=9, column=6, padx=5, pady=5)

        # ---------------------- Router Mapping Section ---------------------- #
        tk.Label(self.main_frame, text="Add Router Mapping", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=10, column=0, sticky="w", padx=10, pady=5)

        self.router_host = tk.StringVar()
        self.router_network = tk.StringVar()

        tk.Label(self.main_frame, text="Router", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=11, column=0)
        self.router_host_dropdown = ttk.Combobox(self.main_frame, textvariable=self.router_host,
                                                 values=[], width=15, style="CustomCombobox.TCombobox")
        self.router_host_dropdown.grid(row=11, column=1, padx=5, pady=5)

        tk.Label(self.main_frame, text="Network", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=11, column=2)
        self.router_network_dropdown = ttk.Combobox(self.main_frame, textvariable=self.router_network,
                                                    values=[], width=15, style="CustomCombobox.TCombobox")
        self.router_network_dropdown.grid(row=11, column=3, padx=5, pady=5)

        tk.Button(self.main_frame, text="Add Router Mapping",
                  command=self.add_router_mapping,
                  bg="#214f07", fg="white", activebackground="#39FF14",
                  activeforeground="white"
        ).grid(row=11, column=4, padx=5, pady=5)

        # ---------------------- Groups Section ---------------------- #
        tk.Label(self.main_frame, text="Add Group", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=12, column=0, sticky="w", padx=10, pady=5)

        self.group_name = tk.StringVar()
        tk.Label(self.main_frame, text="Group Name", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=13, column=0)
        tk.Entry(self.main_frame, textvariable=self.group_name, width=15,
                 bg="#333333", fg="white", insertbackground="white"
        ).grid(row=13, column=1, padx=5, pady=5)

        tk.Label(self.main_frame, text="Select Hosts", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=13, column=2)
        self.hosts_select = tk.Listbox(self.main_frame, selectmode=tk.MULTIPLE,
                                       bg="#333333", fg="white", height=3, width=30)
        self.hosts_select.grid(row=13, column=3, padx=5, pady=5)

        tk.Button(self.main_frame, text="Add Group", command=self.add_groups,
                  bg="#214f07", fg="white", activebackground="#39FF14",
                  activeforeground="white"
        ).grid(row=13, column=4, padx=5, pady=5)

        # ---------------------- Container Section ---------------------- #
        self.containers_frame = tk.Frame(self.main_frame, bg="#00304E")
        self.containers_frame.grid(row=14, column=0, columnspan=7, sticky="ew", padx=10, pady=5)

        tk.Label(self.containers_frame, text="Add Container", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=0, column=0, sticky="w", padx=10, pady=3)

        self.container_name = tk.StringVar()
        self.container_image = tk.StringVar(value=self.available_images[0])
        self.container_dockerfile = tk.StringVar()

        tk.Label(self.containers_frame, text="Container Name", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=1, column=0)
        tk.Entry(self.containers_frame, textvariable=self.container_name, width=15,
                 bg="#333333", fg="white", insertbackground="white"
        ).grid(row=1, column=1, padx=5, pady=3)

        tk.Label(self.containers_frame, text="Select Image", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=1, column=2)
        ttk.Combobox(self.containers_frame, values=self.available_images,
                     textvariable=self.container_image, width=15,
                     style="CustomCombobox.TCombobox"
        ).grid(row=1, column=3, padx=5, pady=3)

        tk.Label(self.containers_frame, text="Dockerfile", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=1, column=4)
        tk.Entry(self.containers_frame, textvariable=self.container_dockerfile, width=15,
                 bg="#333333", fg="white", insertbackground="white"
        ).grid(row=1, column=5, padx=5, pady=3)

        tk.Button(self.containers_frame, text="Add Container", command=self.add_container,
                  bg="#214f07", fg="white", activebackground="#39FF14",
                  activeforeground="white"
        ).grid(row=1, column=6, padx=10, pady=3)

        # ---------------------- Container Mappings Section ---------------------- #
        self.container_mappings_frame = tk.Frame(self.main_frame, bg="#00304E")
        self.container_mappings_frame.grid(row=15, column=0, columnspan=7, sticky="ew", padx=10, pady=5)

        tk.Label(self.container_mappings_frame, text="Add Container Mapping", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=0, column=0, sticky="w", padx=10, pady=3)

        self.mapping_container_var = tk.StringVar()
        self.mapping_port_var = tk.StringVar()

        tk.Label(self.container_mappings_frame, text="Container", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=1, column=0)
        self.mapping_container_dropdown = ttk.Combobox(
            self.container_mappings_frame,
            textvariable=self.mapping_container_var,
            values=[],
            width=15,
            style="CustomCombobox.TCombobox"
        )
        self.mapping_container_dropdown.grid(row=1, column=1, padx=5, pady=3)

        tk.Label(self.container_mappings_frame, text="Select Docker Host", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=1, column=2)
        self.docker_host_var = tk.StringVar()
        self.docker_host_dropdown = ttk.Combobox(
            self.container_mappings_frame,
            textvariable=self.docker_host_var,
            values=[],
            width=15,
            style="CustomCombobox.TCombobox"
        )
        self.docker_host_dropdown.grid(row=1, column=3, padx=5, pady=3)

        tk.Label(self.container_mappings_frame, text="Port", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=1, column=4)
        tk.Entry(self.container_mappings_frame, textvariable=self.mapping_port_var, width=8,
                 bg="#333333", fg="white", insertbackground="white"
        ).grid(row=1, column=5, padx=5, pady=3)

        tk.Button(self.container_mappings_frame, text="Add Container Mapping", command=self.add_container_mapping,
                  bg="#214f07", fg="white", activebackground="#39FF14",
                  activeforeground="white"
        ).grid(row=1, column=6, padx=10, pady=3)

        # ---------------------- Generate Topology Button ---------------------- #
        tk.Button(self.main_frame, text="Generate Topology", command=self.generate_topology,
                  bg="#214f07", fg="white", activebackground="#39FF14",
                  activeforeground="white"
        ).grid(row=16, column=0, columnspan=7, sticky="ew", padx=12, pady=10)

        # ---------------------- Hosts Listbox ---------------------- #
        tk.Label(self.main_frame, text="Hosts Added:", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=17, column=0, sticky="w", padx=10, pady=5)
        self.hosts_list = tk.Listbox(self.main_frame, height=2, state="normal",
                                     bg="#333333", fg="white",
                                     selectbackground="#444444",
                                     selectforeground="white")
        self.hosts_list.grid(row=18, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        hosts_scrollbar = tk.Scrollbar(self.main_frame, orient="vertical", command=self.hosts_list.yview)
        hosts_scrollbar.grid(row=18, column=2, sticky="ns")
        self.hosts_list.config(yscrollcommand=hosts_scrollbar.set)

        # ---------------------- Routers Listbox ---------------------- #
        tk.Label(self.main_frame, text="Routers Added:", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=19, column=0, sticky="w", padx=10, pady=5)
        self.routers_list = tk.Listbox(self.main_frame, height=2, state="normal",
                                       bg="#333333", fg="white",
                                       selectbackground="#444444",
                                       selectforeground="white")
        self.routers_list.grid(row=20, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        routers_scrollbar = tk.Scrollbar(self.main_frame, orient="vertical", command=self.routers_list.yview)
        routers_scrollbar.grid(row=20, column=2, sticky="ns")
        self.routers_list.config(yscrollcommand=routers_scrollbar.set)

        # ---------------------- Networks Listbox ---------------------- #
        tk.Label(self.main_frame, text="Networks Added:", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=21, column=0, sticky="w", padx=10, pady=5)
        self.networks_list = tk.Listbox(self.main_frame, height=2, state="normal",
                                        bg="#333333", fg="white",
                                        selectbackground="#444444",
                                        selectforeground="white")
        self.networks_list.grid(row=22, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        networks_scrollbar = tk.Scrollbar(self.main_frame, orient="vertical", command=self.networks_list.yview)
        networks_scrollbar.grid(row=22, column=2, sticky="ns")
        self.networks_list.config(yscrollcommand=networks_scrollbar.set)

        # ---------------------- Network Mappings Listbox ---------------------- #
        tk.Label(self.main_frame, text="Network Mappings:", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=17, column=4, sticky="w", padx=10, pady=5)
        self.network_mappings_list = tk.Listbox(self.main_frame, height=2, width=50, state="normal",
                                                bg="#333333", fg="white",
                                                selectbackground="#444444",
                                                selectforeground="white")
        self.network_mappings_list.grid(row=18, column=4, columnspan=2, sticky="nsew", padx=10, pady=5)
        network_mappings_scrollbar = tk.Scrollbar(self.main_frame, orient="vertical",
                                                  command=self.network_mappings_list.yview)
        network_mappings_scrollbar.grid(row=18, column=6, sticky="ns")
        self.network_mappings_list.config(yscrollcommand=network_mappings_scrollbar.set)

        # ---------------------- Router Mappings Listbox ---------------------- #
        tk.Label(self.main_frame, text="Router Mappings:", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=19, column=4, sticky="w", padx=10, pady=5)
        self.router_mappings_list = tk.Listbox(self.main_frame, height=2, width=50, state="normal",
                                               bg="#333333", fg="white",
                                               selectbackground="#444444",
                                               selectforeground="white")
        self.router_mappings_list.grid(row=20, column=4, columnspan=2, sticky="nsew", padx=10, pady=5)
        router_mappings_scrollbar = tk.Scrollbar(self.main_frame, orient="vertical",
                                                 command=self.router_mappings_list.yview)
        router_mappings_scrollbar.grid(row=20, column=6, sticky="ns")
        self.router_mappings_list.config(yscrollcommand=router_mappings_scrollbar.set)

        # ---------------------- Groups Listbox ---------------------- #
        tk.Label(self.main_frame, text="Groups Added:", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=21, column=4, sticky="w", padx=10, pady=5)
        self.groups_list = tk.Listbox(self.main_frame, height=2, state="normal",
                                      bg="#333333", fg="white",
                                      selectbackground="#444444",
                                      selectforeground="white")
        self.groups_list.grid(row=22, column=4, columnspan=2, sticky="nsew", padx=10, pady=5)
        groups_scrollbar = tk.Scrollbar(self.main_frame, orient="vertical", command=self.groups_list.yview)
        groups_scrollbar.grid(row=22, column=6, sticky="ns")
        self.groups_list.config(yscrollcommand=groups_scrollbar.set)

        # ---------------------- Containers Listbox ---------------------- #
        tk.Label(self.main_frame, text="Containers Added:", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=24, column=0, sticky="w", padx=10, pady=5)
        self.containers_list = tk.Listbox(self.main_frame, height=2, state="normal",
                                          bg="#333333", fg="white",
                                          selectbackground="#444444",
                                          selectforeground="white")
        self.containers_list.grid(row=25, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

        tk.Label(self.main_frame, text="Container Mappings:", font=("Helvetica", 12),
                 bg="#00304E", fg="#39FF14").grid(row=24, column=4, sticky="w", padx=10, pady=5)
        self.container_mappings_list = tk.Listbox(self.main_frame, height=2, width=50, state="normal",
                                                  bg="#333333", fg="white",
                                                  selectbackground="#444444",
                                                  selectforeground="white")
        self.container_mappings_list.grid(row=25, column=4, columnspan=2, sticky="nsew", padx=10, pady=5)

        # ---------------------- Footer ---------------------- #
        tk.Label(
            self.main_frame, text="Made by Gabriel Tabacaru for CYBERCOR © 2025",
            font=("Helvetica", 10), bg="#007acc", fg="white", pady=10
        ).grid(row=29, column=0, columnspan=10, sticky="ew")

        # Initially hide container frames
        self.show_or_hide_container_frames()

    # ---------------------- Host Logic ---------------------- #
    def add_host(self):
        # Only store 'hidden' if True
        host = {
            "name": self.host_name.get().strip(),
            "base_box": {
                "image": self.host_image.get().strip(),
                "man_user": self.host_user.get().strip()
            },
            "flavor": self.host_flavor.get().strip(),
        }
        # If hidden is True, store it
        if self.host_hidden.get():
            host["hidden"] = True

        # Whether Docker is selected or not, it only affects container logic
        # but we do store it if we want to check it in show_or_hide_container_frames.
        host["docker"] = self.host_docker.get()

        self.hosts.append(host)
        self.hosts_list.insert(
            tk.END,
            f"Host: {host['name']}, Image: {host['base_box']['image']}"
        )
        self.hosts_select.insert(tk.END, host["name"])

        # Reset
        self.host_name.set("")
        self.host_image.set(self.available_images[0])
        self.host_flavor.set(self.available_flavors[0])
        self.host_user.set(self.available_users[0])
        self.host_hidden.set(False)
        self.host_docker.set(False)

        self.refresh_dropdowns()
        self.show_or_hide_container_frames()

    def show_or_hide_container_frames(self):
        """
        Show container frames only if there's at least one host with docker=True.
        Also refresh Docker host list for container mapping.
        """
        docker_hosts = [h["name"] for h in self.hosts if h.get("docker") is True]
        self.docker_host_dropdown["values"] = docker_hosts

        if docker_hosts:
            self.containers_frame.grid()            # Show containers frame
            self.container_mappings_frame.grid()    # Show container mappings frame
        else:
            self.containers_frame.grid_remove()     # Hide containers frame
            self.container_mappings_frame.grid_remove()  # Hide container mappings frame

    # ---------------------- Router Logic ---------------------- #
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
        self.routers_list.insert(
            tk.END, f"Router: {router['name']}, Image: {router['base_box']['image']}"
        )

        # Reset
        self.router_name.set("")
        self.router_image.set(self.available_images[0])
        self.router_flavor.set(self.available_flavors[0])
        self.router_user.set(self.available_users[0])

        self.refresh_dropdowns()

    # ---------------------- Network Logic ---------------------- #
    def add_network(self):
        network = {
            "name": self.network_name.get().strip(),
            "cidr": self.network_cidr.get().strip(),
            "accessible_by_user": self.network_accessible.get()
        }
        self.networks.append(network)
        self.networks_list.insert(
            tk.END, f"Network: {network['name']}, CIDR: {network['cidr']}"
        )

        # Reset
        self.network_name.set("")
        self.network_cidr.set("")
        self.network_accessible.set(False)

        self.refresh_dropdowns()

    def add_network_mapping(self):
        if not self.hosts or not self.networks:
            messagebox.showerror("Error", "Add hosts and networks first!")
            return

        host_name = self.net_host.get().strip()
        network_name = self.net_network.get().strip()
        last_octet = self.net_last_octet.get().strip()

        selected_network = next((n for n in self.networks if n["name"] == network_name), None)
        if not selected_network:
            messagebox.showerror("Error", "Invalid network selected!")
            return

        cidr_prefix = ".".join(selected_network["cidr"].split(".")[:3])
        ip = f"{cidr_prefix}.{last_octet}"

        mapping = {
            "host": host_name,
            "network": network_name,
            "ip": ip
        }
        self.net_mappings.append(mapping)
        self.network_mappings_list.insert(
            tk.END,
            f"Host: {host_name} -> Network: {network_name} (IP: {ip})"
        )

        # Reset
        self.net_host.set("")
        self.net_network.set("")
        self.net_last_octet.set("")

    # ---------------------- Router Mapping Logic ---------------------- #
    def add_router_mapping(self):
        if not self.routers or not self.networks:
            messagebox.showerror("Error", "Add routers and networks first!")
            return

        router_name = self.router_host.get().strip()
        network_name = self.router_network.get().strip()

        selected_network = next((n for n in self.networks if n["name"] == network_name), None)
        if not selected_network:
            messagebox.showerror("Error", "Invalid network selected!")
            return

        cidr_prefix = ".".join(selected_network["cidr"].split(".")[:3])
        ip = f"{cidr_prefix}.1"

        mapping = {
            "router": router_name,
            "network": network_name,
            "ip": ip
        }
        self.router_mappings.append(mapping)
        self.router_mappings_list.insert(
            tk.END,
            f"Router: {router_name} -> Network: {network_name} (IP: {ip})"
        )

        # Reset
        self.router_host.set("")
        self.router_network.set("")

    # ---------------------- Groups Logic ---------------------- #
    def add_groups(self):
        group_name = self.group_name.get().strip()
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
        self.groups_list.insert(
            tk.END, f"Group: {group_name}, Hosts: {', '.join(selected_hosts)}"
        )

        # Reset
        self.group_name.set("")
        self.hosts_select.selection_clear(0, tk.END)

    # ---------------------- Containers Logic ---------------------- #
    def add_container(self):
        """
        Add container. If 'dockerfile' is specified, skip 'image'.
        Also create a directory <dockerfile>/ in the main folder if dockerfile is specified.
        """
        name = self.container_name.get().strip()
        image = self.container_image.get().strip()
        dockerfile = self.container_dockerfile.get().strip()

        if not name:
            messagebox.showerror("Error", "Container name cannot be empty!")
            return

        container_entry = {"name": name}
        if dockerfile:
            container_entry["dockerfile"] = dockerfile
            base_dir = os.path.join(os.getcwd(), self.name.get())
            os.makedirs(base_dir, exist_ok=True)
            dockerfile_dir = os.path.join(base_dir, dockerfile)
            os.makedirs(dockerfile_dir, exist_ok=True)
        else:
            container_entry["image"] = image

        self.containers.append(container_entry)
        self.containers_list.insert(
            tk.END,
            f"Container: {name} => " +
            (f"Dockerfile: {dockerfile}" if dockerfile else f"Image: {image}")
        )

        # Reset
        self.container_name.set("")
        self.container_image.set(self.available_images[0])
        self.container_dockerfile.set("")

        self.refresh_container_dropdown()

    def add_container_mapping(self):
        """
        Add container mapping with a single Docker host and numeric port.
        """
        container_name = self.mapping_container_var.get().strip()
        if not container_name:
            messagebox.showerror("Error", "Select a container!")
            return

        docker_host = self.docker_host_var.get().strip()
        if not docker_host:
            messagebox.showerror("Error", "Select a Docker host!")
            return

        port_str = self.mapping_port_var.get().strip()
        if not port_str:
            messagebox.showerror("Error", "Port cannot be empty!")
            return

        mapping = {
            "container": container_name,
            "host": docker_host,
            "port": port_str  # We'll parse as int in save_containers
        }
        self.container_mappings.append(mapping)
        self.container_mappings_list.insert(
            tk.END, f"Container: {container_name}, Host: {docker_host}, Port: {port_str}"
        )

        # Reset
        self.mapping_container_var.set("")
        self.docker_host_var.set("")
        self.mapping_port_var.set("")

    def refresh_container_dropdown(self):
        """
        Refresh the container dropdown for container mappings.
        """
        container_names = [c["name"] for c in self.containers]
        self.mapping_container_dropdown["values"] = container_names

    # ---------------------- Refresh Logic ---------------------- #
    def refresh_dropdowns(self):
        """
        Refresh host, network, and router dropdowns.
        """
        self.net_host_dropdown["values"] = [host["name"] for host in self.hosts]
        self.net_network_dropdown["values"] = [net["name"] for net in self.networks]
        self.router_host_dropdown["values"] = [router["name"] for router in self.routers]
        self.router_network_dropdown["values"] = [net["name"] for net in self.networks]

        self.refresh_container_dropdown()

    # ---------------------- Generate Topology ---------------------- #
    def generate_topology(self):
        """
        Create topology.yml and containers.yml, then build the dynamic notebook for editing folders/files.
        """
        if not self.name.get().strip():
            messagebox.showerror("Error", "Topology name cannot be empty!")
            return

        base_dir = os.path.join(os.getcwd(), self.name.get())
        output_file = save_topology(
            self.name.get(),
            self.hosts,
            self.routers,
            self.networks,
            self.net_mappings,
            self.router_mappings,
            self.groups
        )

        # If we have containers, also create containers.yml
        if self.containers or self.container_mappings:
            containers_file = save_containers(base_dir, self.containers, self.container_mappings)
            msg = f"Topology saved at: {output_file}\nContainers saved at: {containers_file}"
        else:
            msg = f"Topology saved at: {output_file}"

        # Build or rebuild the folder/file notebook
        self.build_files_notebook(base_dir)

        messagebox.showinfo("Success", msg)

    # ---------------------- Folder/File Notebook Logic ---------------------- #
    def build_files_notebook(self, base_dir):
        """
        Create a ttk.Notebook that displays a tab for each folder and file
        under <base_dir>/provisioning/roles. Allows file upload and inline editing.
        """
        # If the notebook already exists, destroy it and rebuild
        if self.files_notebook:
            self.files_notebook.destroy()

        self.files_notebook = ttk.Notebook(self.main_frame)
        self.files_notebook.configure(style="TNotebook")
        self.files_notebook.grid(row=30, column=0, columnspan=10, sticky="nsew", padx=10, pady=10)

        roles_dir = os.path.join(base_dir, "provisioning", "roles")
        if not os.path.isdir(roles_dir):
            return

        # For each host folder in roles
        for host_folder in sorted(os.listdir(roles_dir)):
            host_path = os.path.join(roles_dir, host_folder)
            if os.path.isdir(host_path):
                # Create a frame tab for the folder
                folder_tab = tk.Frame(self.files_notebook, bg="#00304E")
                self.files_notebook.add(folder_tab, text=f"{host_folder}")

                # Upload button for new files in this folder
                upload_btn = tk.Button(
                    folder_tab, text="Upload File",
                    command=lambda p=host_path: self.upload_file(p),
                    bg="#214f07", fg="white", activebackground="#39FF14"
                )
                upload_btn.pack(pady=5, anchor="w")

                # Recursively add subfolders/files
                self.create_folder_view(folder_tab, host_path)

    def create_folder_view(self, parent_frame, folder_path):
        """
        Create sub-tabs or a simple listing for each file in folder_path.
        If it's a file, add a new sub-tab with an editable text widget.
        """
        # We can either list each subfolder or each file. Let's keep it simple:
        # For each subfolder or file in folder_path, create a sub-tab if it's a file,
        # or recursively show more content if it's a folder.

        # Notebook for the items in this folder
        folder_notebook = ttk.Notebook(parent_frame)
        folder_notebook.configure(style="TNotebook")
        folder_notebook.pack(fill="both", expand=True)

        for item in sorted(os.listdir(folder_path)):
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):
                # Create a sub-tab for the subfolder
                subfolder_tab = tk.Frame(folder_notebook, bg="#00304E")
                folder_notebook.add(subfolder_tab, text=f"[Dir] {item}")

                # A button to upload inside subfolder
                upload_btn = tk.Button(
                    subfolder_tab, text="Upload File",
                    command=lambda p=item_path: self.upload_file(p),
                    bg="#214f07", fg="white", activebackground="#39FF14"
                )
                upload_btn.pack(pady=5, anchor="w")

                # Recursively show contents
                self.create_folder_view(subfolder_tab, item_path)

            else:
                # It's a file, create a tab with a text widget
                file_tab = tk.Frame(folder_notebook, bg="#00304E")
                folder_notebook.add(file_tab, text=item)
                # A text widget for editing
                text_widget = tk.Text(file_tab, wrap="word", bg="#333333", fg="white")
                text_widget.pack(fill="both", expand=True)

                # Load file contents
                try:
                    with open(item_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    text_widget.insert("1.0", content)
                except Exception as e:
                    text_widget.insert("1.0", f"Error reading file: {e}")

                # Bind changes for autosave
                text_widget.bind("<KeyRelease>", lambda event, p=item_path, w=text_widget: self.autosave_file(p, w))

    def upload_file(self, target_folder):
        """
        Upload a file from the user's computer into 'target_folder'.
        After upload, rebuild the notebook to show the newly added file.
        """
        file_path = filedialog.askopenfilename()
        if not file_path:
            return  # user cancelled

        file_name = os.path.basename(file_path)
        dest_path = os.path.join(target_folder, file_name)
        try:
            # Copy file
            with open(file_path, "rb") as src, open(dest_path, "wb") as dst:
                dst.write(src.read())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload file: {e}")
            return

        messagebox.showinfo("Success", f"Uploaded {file_name} to {target_folder}")
        # Rebuild the notebook
        base_dir = os.path.join(os.getcwd(), self.name.get())
        self.build_files_notebook(base_dir)

    def autosave_file(self, file_path, text_widget):
        """
        Automatically save the file whenever the text changes.
        """
        try:
            content = text_widget.get("1.0", tk.END)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            # If we fail to autosave, optionally show error or ignore
            pass


# ---------------------- Main ---------------------- #
if __name__ == "__main__":
    root = tk.Tk()
    app = TopologyApp(root)
    root.mainloop()
