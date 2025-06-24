import uuid
import streamlit as st
from datetime import datetime
from typing import List, Dict, Any
from aws_agent_chatbot import AWSAgentChatbot
from utils import display_content_with_formatting, format_file_size
# import logging

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

def init_session_state():
    """Initialize Streamlit session state"""
    # Initialize the chatbot
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = None

    if 'agents' not in st.session_state:
        st.session_state.agents = []

    if 'selected_agent' not in st.session_state:
        st.session_state.selected_agent = None
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    # Session state keys for uploader reset
    if 'uploader_key' not in st.session_state:
        st.session_state.uploader_key = 0
    
    # Add conversation context tracking
    if 'conversation_context' not in st.session_state:
        st.session_state.conversation_context = {
            'current_agent': None,
            'session_start_time': datetime.now(),
            'message_count': 0,
            'last_agent_switch': None
        }

def setup_sidebar():
    """Setup sidebar for AWS configuration and navigation"""
    if 'is_logged_in' not in st.session_state:
        st.session_state.is_logged_in = False

    # Initialize selected page in session state if not exists
    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = "🤖 Agents"

    def on_page_change():
        st.session_state.selected_page = st.session_state.nav_radio

    if not st.session_state.is_logged_in:
        st.sidebar.title("🔧 AWS Configuration")
        
        # AWS Region
        region = st.sidebar.selectbox(
            "AWS Region",
            ["us-west-2", "us-east-1", "eu-west-1", "ap-southeast-1"],
            index=0,
            help="Select the region where your Bedrock Agent is deployed"
        )
        
        # Credentials input
        st.sidebar.subheader("AWS Credentials")
        cred_method = st.sidebar.radio(
            "Authentication Method",
            ["Use Default Credentials", "Enter Credentials Manually"]
        )
        
        aws_access_key = None
        aws_secret_key = None
        
        if cred_method == "Enter Credentials Manually":
            aws_access_key = st.sidebar.text_input("AWS Access Key ID", type="password", help="Enter your AWS Access Key ID")
            aws_secret_key = st.sidebar.text_input("AWS Secret Access Key", type="password", help="Enter your AWS Secret Access Key")
            
            # Validate credential format
            if aws_access_key and not aws_access_key.startswith('AKIA'):
                st.sidebar.warning("⚠️ Access Key ID should start with 'AKIA'")
            if aws_secret_key and len(aws_secret_key) != 40:
                st.sidebar.warning("⚠️ Secret Access Key should be 40 characters long")
        
        # Connect button
        if st.sidebar.button("🔌 Connect to AWS"):
            # Validate credentials if manual method is selected
            if cred_method == "Enter Credentials Manually":
                if not aws_access_key or not aws_secret_key:
                    st.sidebar.error("❌ Please provide both Access Key ID and Secret Access Key")
                    return
                if not aws_access_key.startswith('AKIA'):
                    st.sidebar.error("❌ Invalid Access Key ID format")
                    return
                if len(aws_secret_key) != 40:
                    st.sidebar.error("❌ Invalid Secret Access Key format")
                    return
            
            try:
                with st.spinner("Connecting to AWS Bedrock Agents..."):
                    client = AWSAgentChatbot(
                        region_name=region,
                        aws_access_key_id=aws_access_key,
                        aws_secret_access_key=aws_secret_key
                    )
                    
                    # Test the connection and credentials
                    test_result = client.test_credentials()
                    
                    if test_result['status'] == 'error':
                        st.sidebar.error(f"❌ Connection test failed: {test_result['error']}")
                        
                        # Show debug information for troubleshooting
                        with st.sidebar.expander("🔧 Debug Information", expanded=False):
                            debug_info = client.debug_connection()
                            st.write("**Connection Debug Info:**")
                            st.write(f"- Region: {debug_info['region']}")
                            st.write(f"- Credential Method: {test_result['credential_method']}")
                            st.write(f"- Has Access Key: {debug_info['has_access_key']}")
                            st.write(f"- Has Secret Key: {debug_info['has_secret_key']}")
                            st.write(f"- Access Key Prefix: {debug_info['access_key_prefix']}")
                            st.write(f"- S3 Test: {debug_info['s3_test']}")
                            st.write(f"- Bedrock Test: {debug_info['bedrock_test']}")
                        
                        return
                    
                    # Test the connection by listing agents
                    agents = client.list_agents()
                    
                    if not agents:
                        st.sidebar.warning("⚠️ No agents found. Please ensure you have agents created in AWS Bedrock.")
                    
                    st.session_state.chatbot = client
                    st.session_state.agents = agents
                    st.session_state.is_logged_in = True
                    
                    # Store connection info (without credentials)
                    st.session_state.connection_info = {
                        'region': region,
                        'credential_method': cred_method,
                        'connected_at': datetime.now(),
                        'agent_count': len(agents) if agents else 0,
                        'user_arn': test_result.get('user_arn', 'Unknown'),
                        'account_id': test_result.get('account_id', 'Unknown')
                    }

                    # Only set initial agent and alias if none selected
                    if not st.session_state.selected_agent and agents:
                        first_agent = agents[0]
                        aliases = client.list_agent_aliases(first_agent['agentId'])
                        if aliases:
                            # Sort aliases by creation date (newest first)
                            sorted_aliases = sorted(aliases, 
                                key=lambda x: x.get('lastUpdatedDateTime', x.get('creationDateTime', '')), 
                                reverse=True)
                            st.session_state.chat_alias_id = sorted_aliases[0]['agentAliasId']
                            st.session_state.selected_agent = first_agent
                    
                    st.sidebar.success("✅ Connected successfully!")
                    st.rerun()
                
            except Exception as e:
                error_msg = str(e)
                st.sidebar.error(f"❌ Connection failed: {error_msg}")
                
                # Provide helpful debugging information
                if "credentials" in error_msg.lower() or "invalid" in error_msg.lower():
                    st.sidebar.info("💡 Tip: Check your AWS credentials and permissions")
                elif "region" in error_msg.lower():
                    st.sidebar.info("💡 Tip: Verify the selected region supports Bedrock Agents")
                elif "access denied" in error_msg.lower():
                    st.sidebar.info("💡 Tip: Ensure your IAM user/role has Bedrock permissions")
                elif "timeout" in error_msg.lower():
                    st.sidebar.info("💡 Tip: Check your internet connection and try again")
                elif "not found" in error_msg.lower():
                    st.sidebar.info("💡 Tip: Verify the region and service availability")
                else:
                    st.sidebar.info("💡 Tip: Check your AWS configuration and permissions")
    else:
        # Sidebar for configuration and file management
        with st.sidebar:
            # Show current connection info
            st.success(f"✅ Connected to {st.session_state.chatbot.region_name}")
            
            # Display connection details
            if 'connection_info' in st.session_state:
                with st.expander("🔗 Connection Details", expanded=False):
                    st.write(f"**Region:** {st.session_state.connection_info['region']}")
                    st.write(f"**Method:** {st.session_state.connection_info['credential_method']}")
                    st.write(f"**Connected:** {st.session_state.connection_info['connected_at'].strftime('%H:%M:%S')}")
                    st.write(f"**Agents Found:** {st.session_state.connection_info['agent_count']}")
                    st.write(f"**Account ID:** {st.session_state.connection_info['account_id']}")
                    st.write(f"**User ARN:** {st.session_state.connection_info['user_arn']}")
            
            # Disconnect button
            if st.button("🔌 Disconnect"):
                # Clear session state
                st.session_state.is_logged_in = False
                st.session_state.chatbot = None
                st.session_state.agents = []
                st.session_state.selected_agent = None
                st.session_state.messages = []
                st.session_state.session_id = str(uuid.uuid4())
                st.session_state.conversation_context = {
                    'current_agent': None,
                    'session_start_time': datetime.now(),
                    'message_count': 0,
                    'last_agent_switch': None
                }
                if 'connection_info' in st.session_state:
                    del st.session_state.connection_info
                st.success("Disconnected successfully!")
                st.rerun()
            
            st.divider()
            
            # Navigation menu
            st.title("🧭 Navigation")

            # Use on_change callback for the radio button
            st.radio(
                "Go to",
                ["🤖 Agents", "💬 Chat", "📈 History", "📚 Knowledge Base"],
                key="nav_radio",
                on_change=on_page_change,
                index=["🤖 Agents", "💬 Chat", "📈 History", "📚 Knowledge Base"].index(st.session_state.selected_page)
            )
            
            # Show agent info if selected
            if st.session_state.selected_agent:
                st.success(f"🤖 Selected Agent: {st.session_state.selected_agent['agentName']}")

            # st.header("⚙️ Configuration")
            
            # # Configuration inputs
            # s3_bucket = st.text_input("S3 Bucket Name", value=st.session_state.chatbot.s3_bucket)
            # s3_bucket_folder = st.text_input("S3 Bucket Folder Name", value=st.session_state.chatbot.s3_bucket_folder)
            # knowledge_base_id = st.text_input("Knowledge Base ID", value=st.session_state.chatbot.knowledge_base_id)
            # agent_id = st.text_input("Agent ID", value=st.session_state.chatbot.agent_id)
            # agent_alias_id = st.text_input("Agent Alias ID", value=st.session_state.chatbot.agent_alias_id)
            
            # # Update configuration
            # if st.button("Update Configuration"):
            #     st.session_state.chatbot.s3_bucket = s3_bucket
            #     st.session_state.chatbot.s3_bucket_folder = s3_bucket_folder
            #     st.session_state.chatbot.knowledge_base_id = knowledge_base_id
            #     st.session_state.chatbot.agent_id = agent_id
            #     st.session_state.chatbot.agent_alias_id = agent_alias_id
            #     st.success("Configuration updated!")
            
            st.divider()
            
            # Session management
            st.header("🔄 Session")
            if st.button("New Session"):
                st.session_state.session_id = str(uuid.uuid4())
                st.session_state.messages = []
                # Reset conversation context
                st.session_state.conversation_context = {
                    'current_agent': st.session_state.selected_agent['agentId'] if st.session_state.selected_agent else None,
                    'session_start_time': datetime.now(),
                    'message_count': 0,
                    'last_agent_switch': None
                }
                st.success("New session started!")
            
            st.caption(f"Session ID: {st.session_state.session_id[:8]}...")
            
            # Display conversation context info
            if st.session_state.conversation_context['message_count'] > 0:
                st.caption(f"Messages in session: {st.session_state.conversation_context['message_count']}")
                session_duration = datetime.now() - st.session_state.conversation_context['session_start_time']
                st.caption(f"Session duration: {session_duration.seconds // 60}m {session_duration.seconds % 60}s")
    
    return st.session_state.is_logged_in

def display_agents_section():
    """Display available agents section with detailed agent analysis"""
    st.header("🤖 Available Agents")
    
    if not st.session_state.agents:
        st.info("No agents found. Please ensure you have agents created in AWS Bedrock.")
        return
    
    # Create agent selection
    agent_options = [f"{agent['agentName']} ({agent['agentId']})" for agent in st.session_state.agents]
    
    # Find current agent index
    current_index = 0
    if st.session_state.selected_agent:
        current_index = next(
            (i for i, opt in enumerate(agent_options) 
             if st.session_state.selected_agent['agentId'] in opt),
            0
        )
    
    # Track previous selection
    if 'previous_agent_selection' not in st.session_state:
        st.session_state.previous_agent_selection = agent_options[current_index]
    
    selected_agent_option = st.selectbox(
        "Select an Agent",
        agent_options,
        index=current_index,
        key="agent_selection"
    )
    
    # Only update if selection changed
    if selected_agent_option != st.session_state.previous_agent_selection:
        st.session_state.previous_agent_selection = selected_agent_option
        # Extract agent ID from selection
        agent_id = selected_agent_option.split('(')[-1].strip(')')
        selected_agent = next(agent for agent in st.session_state.agents if agent['agentId'] == agent_id)
        previous_agent_name = st.session_state.selected_agent['agentName'] if st.session_state.selected_agent else None
        st.session_state.selected_agent = selected_agent
        
        # Update conversation context for agent switch
        st.session_state.conversation_context['last_agent_switch'] = datetime.now()
        st.session_state.conversation_context['current_agent'] = agent_id
        
        # Add context message about agent change
        if previous_agent_name and st.session_state.messages:
            context_msg = {
                "role": "system",
                "content": f"Note: Switching from agent '{previous_agent_name}' to '{selected_agent['agentName']}'. Previous conversation context is maintained.",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "is_context": True
            }
            st.session_state.messages.append(context_msg)
        
        st.rerun()

    if selected_agent_option:
        # Extract agent ID from selection
        agent_id = selected_agent_option.split('(')[-1].strip(')')
        if not st.session_state.selected_agent or st.session_state.selected_agent['agentId'] != agent_id:
            selected_agent = next(agent for agent in st.session_state.agents if agent['agentId'] == agent_id)
            st.session_state.selected_agent = selected_agent
        agent_name = st.session_state.selected_agent['agentName']

        # Load agent aliases and select newest by default
        try:
            aliases = st.session_state.chatbot.list_agent_aliases(agent_id)
            st.session_state.agent_aliases = aliases
            
            if aliases:
                # Sort aliases by creation date (newest first)
                sorted_aliases = sorted(aliases, 
                    key=lambda x: x.get('lastUpdatedDateTime', x.get('creationDateTime', '')), 
                    reverse=True)
                newest_alias = sorted_aliases[0]
                
                # Initialize use_latest in session state if not present
                if 'use_latest_alias' not in st.session_state:
                    st.session_state.use_latest_alias = True
                    st.session_state.chat_alias_id = newest_alias['agentAliasId']
                
                # Add toggle for testing different aliases
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.info(f"🔄 Latest alias: {newest_alias['agentAliasName']}")
                with col2:
                    # Handle toggle state change
                    previous_state = st.session_state.use_latest_alias
                    current_state = st.toggle(
                        "Use Latest Alias",
                        value=previous_state,
                        help="Toggle to test different aliases",
                        key="use_latest_toggle"
                    )
                    
                    # If state changed, update and rerun
                    if current_state != previous_state:
                        st.session_state.use_latest_alias = current_state
                        if current_state:  # If switching to latest
                            st.session_state.chat_alias_id = newest_alias['agentAliasId']
                        st.rerun()
                
                if st.session_state.use_latest_alias:
                    if st.session_state.chat_alias_id != newest_alias['agentAliasId']:
                        st.session_state.chat_alias_id = newest_alias['agentAliasId']
                else:
                    alias_options = [f"{alias['agentAliasName']} ({alias['agentAliasId']})" for alias in aliases]
                    # Find current index for the selectbox
                    current_index = 0
                    if st.session_state.chat_alias_id:
                        current_index = next(
                            (i for i, opt in enumerate(alias_options) 
                             if st.session_state.chat_alias_id in opt),
                            0
                        )
                    
                    # Handle alias selection change
                    if 'previous_alias_selection' not in st.session_state:
                        st.session_state.previous_alias_selection = alias_options[current_index]
                    
                    selected_alias_option = st.selectbox(
                        "Select an alias for testing:",
                        alias_options,
                        index=current_index,
                        key="agent_section_alias"
                    )
                    
                    # If selection changed, update and rerun
                    if selected_alias_option != st.session_state.previous_alias_selection:
                        st.session_state.previous_alias_selection = selected_alias_option
                        selected_alias_id = selected_alias_option.split('(')[-1].strip(')')
                        if st.session_state.chat_alias_id != selected_alias_id:
                            st.session_state.chat_alias_id = selected_alias_id
                            st.rerun()
            else:
                st.warning("No aliases available. Using version identifiers.")
                if 'use_version' not in st.session_state:
                    st.session_state.use_version = True
                    st.session_state.chat_alias_id = "DRAFT"
                
                # Handle version toggle state change
                previous_version_state = st.session_state.use_version
                current_version_state = st.checkbox(
                    "Use agent version instead of alias",
                    value=previous_version_state,
                    key="use_version_toggle"
                )
                
                # If version toggle state changed, update and rerun
                if current_version_state != previous_version_state:
                    st.session_state.use_version = current_version_state
                    if current_version_state:
                        st.session_state.chat_alias_id = "DRAFT"
                    else:
                        st.session_state.chat_alias_id = None
                    st.rerun()
                
                if st.session_state.use_version:
                    version_input = st.text_input(
                        "Version:",
                        value=st.session_state.chat_alias_id or "DRAFT",
                        key="chat_version"
                    )
                    if st.session_state.chat_alias_id != version_input:
                        st.session_state.chat_alias_id = version_input
                        st.rerun()
                else:
                    st.session_state.chat_alias_id = None
                
        except Exception as e:
            st.error(f"Error loading agent aliases: {str(e)}")
        
        # Display detailed agent information
        try:
            # Get detailed agent information
            agent_details = st.session_state.chatbot.get_agent_details(agent_id)
            
            # Display detailed information
            display_agent_details(agent_name, agent_details)
            
        except Exception as e:
            st.error(f"Error fetching agent details: {str(e)}")
            with st.expander(f"ℹ️ Basic Agent Information"):
                st.markdown(f"""
                **Agent Name:** {agent_name}  
                **Agent ID:** `{agent_id}`
                
                ⚠️ Unable to fetch detailed information. Please check your permissions and try again.
                """)

def display_agent_details(agent_name: str, agent_details: Dict[str, Any]):
    """Display detailed agent information"""
    capabilities = []
    
    # Basic agent information
    agent_id = agent_details.get('agentId', 'Unknown')
    agent_arn = agent_details.get('agentArn', 'Unknown')
    agent_status = agent_details.get('agentStatus', 'Unknown')
    creation_date = agent_details.get('creationDateTime', None)
    last_update = agent_details.get('lastUpdatedDateTime', None)
    
    # Check for capabilities
    if agent_details.get('instruction'):
        capabilities.append("📋 Custom instructions")
    if agent_details.get('foundationModel'):
        capabilities.append("🧠 Foundation Model powered")
    
    # Create configuration tab
    st.markdown("### 📌 Agent Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Agent Configuration**")
        st.write(f"- 🆔 ID: `{agent_id}`")
        status_color = "green" if agent_status == "Active" else "orange"
        st.markdown(f"- 📊 Status: <span style='color: {status_color}'>{agent_status}</span>", unsafe_allow_html=True)
        if agent_details.get('foundationModel'):
            st.write(f"- 🧠 Model: `{agent_details['foundationModel']}`")
        if agent_details.get('inferenceConfiguration'):
            inference = agent_details['inferenceConfiguration']
            if inference.get('temperature'):
                st.write(f"- 🌡️ Temperature: {inference['temperature']}")
            if inference.get('topP'):
                st.write(f"- 📊 Top P: {inference['topP']}")
            if inference.get('maxTokens'):
                st.write(f"- 📝 Max Tokens: {inference['maxTokens']}")
    
    with col2:
        st.markdown("**Timestamps**")
        if creation_date:
            st.write(f"- 📅 Created: {creation_date.strftime('%Y-%m-%d %H:%M:%S UTC') if isinstance(creation_date, datetime) else creation_date}")
        if last_update:
            st.write(f"- 🔄 Last Updated: {last_update.strftime('%Y-%m-%d %H:%M:%S UTC') if isinstance(last_update, datetime) else last_update}")
        if agent_details.get('idleSessionTTLInSeconds'):
            st.write(f"- ⏱️ Session TTL: {agent_details['idleSessionTTLInSeconds']}s")

    if capabilities:
        st.markdown("**🚀 Capabilities**")
        for capability in capabilities:
            st.write(f"- {capability}")
    
    if agent_details.get('instruction'):
        st.markdown("**📝 Agent Instructions**")
        st.code(agent_details['instruction'], language="markdown")

def display_chat_section():
    """Display intelligent conversational chat interface with agent"""
    # Main chat interface
    st.header("💬 Chat Interface")
    
    if not st.session_state.selected_agent:
        st.info("Please select an agent first from the Agents tab.")
        return
    
    # Debug information (collapsible)
    with st.expander("🔧 Debug: Conversation Context", expanded=False):
        st.write("**Session Info:**")
        st.write(f"- Session ID: {st.session_state.session_id}")
        st.write(f"- Current Agent: {st.session_state.selected_agent['agentName']}")
        st.write(f"- Agent ID: {st.session_state.selected_agent['agentId']}")
        st.write(f"- Alias ID: {st.session_state.chat_alias_id}")
        
        st.write("**Conversation Context:**")
        st.write(f"- Message Count: {st.session_state.conversation_context['message_count']}")
        st.write(f"- Session Start: {st.session_state.conversation_context['session_start_time'].strftime('%H:%M:%S')}")
        if st.session_state.conversation_context['last_agent_switch']:
            st.write(f"- Last Agent Switch: {st.session_state.conversation_context['last_agent_switch'].strftime('%H:%M:%S')}")
        
        if st.session_state.messages:
            st.write("**Recent Messages:**")
            for i, msg in enumerate(st.session_state.messages[-5:]):  # Show last 5 messages
                role_icon = "👤" if msg["role"] == "user" else "🤖" if msg["role"] == "assistant" else "⚙️"
                content_preview = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                st.write(f"{role_icon} {msg['role']}: {content_preview}")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            display_content_with_formatting(message["content"])
            # st.markdown(message["content"])

    # Generate initial response (if it's the first message)
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            response = st.session_state.chatbot.invoke_agent(
                agent_id=st.session_state.selected_agent['agentId'],
                agent_alias_id=st.session_state.chat_alias_id,
                user_input='Hello',
                session_id=st.session_state.session_id,
                conversation_history=st.session_state.messages
            )
            display_content_with_formatting(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        # Update conversation context
        st.session_state.conversation_context['message_count'] += 1
        st.session_state.conversation_context['current_agent'] = st.session_state.selected_agent['agentId']
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about your uploaded documents..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Invoke the agent with conversation history
                    response = st.session_state.chatbot.invoke_agent(
                        agent_id=st.session_state.selected_agent['agentId'],
                        agent_alias_id=st.session_state.chat_alias_id,
                        user_input=prompt,
                        session_id=st.session_state.session_id,
                        conversation_history=st.session_state.messages
                    )
                    
                    if response:
                        # st.markdown(response)
                        display_content_with_formatting(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        # Update conversation context
                        st.session_state.conversation_context['message_count'] += 1
                    else:
                        st.error("No response received from agent")
                        
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

def display_knowledge_base_section():
    """Display knowledge base management interface"""
    st.header("📚 Knowledge Base Management")
    
    if not st.session_state.selected_agent:
        st.info("Please select an agent first from the Agents tab.")
        return
    
    # File upload section
    st.subheader("📁 File Upload")
    
    uploaded_files = st.file_uploader(
        "Upload files",
        type=['pdf', 'txt', 'docx', 'csv', 'json', 'md'],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="Upload multiple documents to add to the knowledge base",
        key=f"multi_file_uploader_{st.session_state.uploader_key}"
    )
    
    if uploaded_files:
        if st.button("Upload All Files"):
            with st.spinner("Uploading files..."):
                results = st.session_state.chatbot.upload_multiple_files_to_s3(
                    uploaded_files
                )
            
            # Reset the file uploader after successful upload
            st.session_state.uploader_key += 1

            # Sync the knowledge base
            with st.spinner("Syncing knowledge base..."):
                st.session_state.chatbot.sync_knowledge_base()
    
    st.divider()
    
    # File management
    st.subheader("📄 File Management")
    
    folder_prefix = "upload_files"
    files = st.session_state.chatbot.list_s3_files(folder_prefix)
    
    if files:
        # Group files by folder for better organization
        files_by_folder = {}
        for file in files:
            folder = file['folder'] or 'root'
            if folder not in files_by_folder:
                files_by_folder[folder] = []
            files_by_folder[folder].append(file)
        
        # Display files grouped by folder
        for folder, folder_files in files_by_folder.items():
            with st.expander(f"📁 {folder} ({len(folder_files)} files)", expanded=False):
                for file in folder_files:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📄 {file['name'].split('/')[-1]}")  # Show only filename
                        st.caption(f"Size: {format_file_size(file['size'])} | Modified: {file['modified'].strftime('%Y-%m-%d %H:%M')}")
                    with col2:
                        if st.button(f"🗑️", key=f"del_{file['name']}"):
                            if st.session_state.chatbot.delete_file_from_s3(file['name']):
                                # Sync the knowledge base
                                st.session_state.chatbot.sync_knowledge_base()
                                st.rerun()
    else:
        st.write("No files found")
    
    # Knowledge base status and actions
    st.divider()
    st.subheader("🔄 Knowledge Base Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Sync Knowledge Base", help="Trigger a manual sync of the knowledge base"):
            with st.spinner("Syncing knowledge base..."):
                job_id = st.session_state.chatbot.sync_knowledge_base()
                if job_id:
                    st.success(f"Knowledge base sync initiated. Job ID: {job_id}")
                else:
                    st.error("Failed to initiate knowledge base sync")
    
    with col2:
        if st.button("📊 Query Knowledge Base", help="Test the knowledge base with a sample query"):
            test_query = "What documents are available?"
            results = st.session_state.chatbot.query_knowledge_base(test_query)
            if results:
                st.success(f"Found {len(results)} relevant documents")
                with st.expander("View Results"):
                    for i, result in enumerate(results[:3]):  # Show first 3 results
                        st.write(f"**Result {i+1}:**")
                        st.write(result.get('content', 'No content available')[:200] + "...")
            else:
                st.info("No results found for the test query")

def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="AWS Agent Chatbot",
        page_icon="🤖",
        layout="wide"
    )

    init_session_state()

    st.title("🤖 AWS Agent Chatbot with File Upload")
    st.markdown("Upload documents and chat with an AI agent that can analyze your files using AWS Bedrock.")
    
    # AWS Configuration section in sidebar
    is_logged_in = setup_sidebar()
    
    if not is_logged_in:
        st.info("👈 Please configure your AWS credentials in the sidebar to get started.")
        
        # Show getting started guide
        with st.expander("🚀 Getting Started Guide", expanded=True):
            st.markdown("""
            **Step 1: Configure AWS Credentials**
            - Set up your AWS credentials in the sidebar
            - Select the appropriate region where your agents are deployed
            
            **Step 2: Select Your Agent**
            - Choose from available agents in your account
            - Review the agent configuration and capabilities
            
            **Step 3: Start Conversing**
            - Upload files (TXT, PDF, JSON, CSV, MD) or enter direct input
            - Ask questions, request analysis, or seek assistance
            - Use the conversational interface for interactive sessions
            """)
        return
    
    # Display content based on selected page
    if st.session_state.selected_page == "🤖 Agents":
        display_agents_section()
    elif st.session_state.selected_page == "💬 Chat":
        display_chat_section()
    elif st.session_state.selected_page == "📚 Knowledge Base":
        display_knowledge_base_section()


if __name__ == "__main__":
    main()