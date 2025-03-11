import streamlit as st
import pandas as pd
import random
from backend import get_credentials, initialize_k8s_client, list_workloads_and_images, get_namespace_list

# Define possible configurations
configurations = {
    "GSK": {
        "customers": ["GSK"],
        "clusters": ["gskv-prod", "gsk-non-prod"],
        "zone": "europe-west1",
        "project_id": "gskv-391105",
        "json_key_path": "gke-sa-key-gsk-non-prod.json",
    },
    "EuroAPI": {
        "customers": ["EUROAPI"],
        "clusters": ["euroapi-prod", "euroapi-non-prod"],
        "zone": "europe-north1",
        "project_id": "euroapi-uat",
        "json_key_path": "gke-sa-key-gsk-non-prod.json",
    },
}

# Sidebar Filters
st.sidebar.title("Filters")
selected_customer = st.sidebar.radio("Select Customer", ["GSK", "EuroAPI"], key="customer_select")

# Apply selected configuration
config = configurations[selected_customer]
customers = config["customers"]
clusters = config["clusters"]
zone = config["zone"]
project_id = config["project_id"]
json_key_path = config["json_key_path"]

selected_cluster = st.sidebar.selectbox("Select Cluster", clusters, key="cluster_select")

# Authenticate using the service account (cached for performance)
@st.cache_resource
def get_cached_credentials(json_key_path):
    return get_credentials(json_key_path)

credentials = get_cached_credentials(json_key_path)

# Kubernetes client initialization (only when needed)
if selected_cluster:
    try:
        initialize_k8s_client(selected_cluster, zone, project_id, credentials)
        #st.success(f"Kubernetes client initialized for cluster: {selected_cluster}")
    except Exception as e:
        st.error(f"Failed to initialize Kubernetes client: {e}")
        st.stop()

# Fetch namespaces (cached to reduce API calls)
@st.cache_data
def get_cached_namespaces(cluster):
    return get_namespace_list() if cluster else []

namespaces = get_cached_namespaces(selected_cluster)
namespaces = ["ALL"] + namespaces if namespaces else ["ALL"]

selected_namespace = st.sidebar.selectbox("Select Namespace", namespaces, key="namespace_select")

# Generate sample data (cached)
@st.cache_data
def generate_dummy_data():
    services = ['ServiceX', 'ServiceY', 'ServiceZ', 'ServiceW']
    versions = ['v1.0', 'v1.1', 'v2.0', 'v2.1']
    
    data = []
    for cluster in clusters:
        cluster_namespaces = get_cached_namespaces(cluster)
        for namespace in cluster_namespaces:
            data.append({
                "Customer": random.choice(customers),
                "Service": random.choice(services),
                "Version": random.choice(versions),
                "Namespace": namespace,
                "Cluster": cluster
            })
    
    # Add additional random entries
    for _ in range(40 - len(data)):
        data.append({
            "Customer": random.choice(customers),
            "Service": random.choice(services),
            "Version": random.choice(versions),
            "Namespace": random.choice(namespaces[1:]) if namespaces[1:] else "default",
            "Cluster": random.choice(clusters)
        })

    return pd.DataFrame(data)

df = generate_dummy_data()

# Apply filters dynamically
def filter_data(df, cluster, namespace, customer):
    if cluster != "ALL":
        df = df[df["Cluster"] == cluster]
    if namespace != "ALL":
        df = df[df["Namespace"] == namespace]
    if customer:
        df = df[df["Customer"] == customer]
    return df

filtered_df = filter_data(df, selected_cluster, selected_namespace, selected_customer)

st.write(f"### Cluster: {selected_cluster}, Namespace: {selected_namespace}")
#st.dataframe(filtered_df)

# CSV Download
csv = filtered_df.to_csv(index=False).encode('utf-8')
#st.download_button("Download Filtered Data", csv, f"filtered_data_{selected_cluster}_{selected_namespace}.csv", "text/csv")

# Fetch workloads and images (cached to improve speed)
@st.cache_data
def get_workloads(namespace):
    return list_workloads_and_images(namespace) if namespace != "ALL" else pd.DataFrame()

if st.sidebar.button("Get Workloads and Images"):  
    df_workloads = get_workloads(selected_namespace)
    
    if not df_workloads.empty:
        #st.write(f"### Workloads and Images for Namespace: {selected_namespace}")
        st.dataframe(df_workloads)
        

        csv_workloads = df_workloads.to_csv(index=False).encode('utf-8')
        #st.download_button("Download Workload Data", csv_workloads, f"workloads_{selected_cluster}_{selected_namespace}.csv", "text/csv", key="namespace")
    else:
        st.warning(f"No workloads found in namespace: {selected_namespace}")
