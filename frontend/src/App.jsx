import React, { useState, useEffect, useRef, useMemo } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Search, FileText, Pin, Cpu, MessageSquare, Clock, RefreshCw, Upload, Link2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Detective Archive initialized. Select a case to begin your investigation." }
  ]);
  const [input, setInput] = useState('');
  const [sources, setSources] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState('All');
  const [isLoading, setIsLoading] = useState(false);
  const [activeView, setActiveView] = useState('board');
  const [serverStatus, setServerStatus] = useState('connecting');
  const [isUploading, setIsUploading] = useState(false);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const scrollRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    checkHealth();
    fetchCases();
    fetchTimeline();
    if (activeView === 'trace') fetchTrace();

    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, [selectedCase]); // Removed activeView dependency

  useEffect(() => {
    if (activeView === 'trace') fetchTrace();
  }, [selectedCase, activeView]);

  const fetchCases = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/cases`);
      setCases(response.data.cases);
    } catch (error) {
      console.error('Error fetching cases:', error);
    }
  };

  const checkHealth = async () => {
    try {
      await axios.get(`${API_BASE_URL}/health`);
      setServerStatus('connected');
    } catch (error) {
      setServerStatus('error');
    }
  };

  const fetchTimeline = async () => {
    const cacheKey = `timeline_${selectedCase}`;
    const cached = sessionStorage.getItem(cacheKey);
    if (cached) {
      setTimeline(JSON.parse(cached));
      return;
    }

    try {
      const response = await axios.get(`${API_BASE_URL}/timeline?case_id=${selectedCase}`);
      setTimeline(response.data.timeline);
      sessionStorage.setItem(cacheKey, JSON.stringify(response.data.timeline));
    } catch (error) {
      console.error('Error fetching timeline:', error);
    }
  };


  const fetchTrace = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/trace?case_id=${selectedCase}`);
      setGraphData(response.data);
    } catch (error) {
      console.error('Error fetching trace:', error);
    }
  };

  const handleIngest = async () => {
    setIsLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/ingest`);
      fetchCases();
      fetchTimeline();
      setMessages(prev => [...prev, { role: 'assistant', content: 'Case files updated. I have indexed the new evidence.' }]);
    } catch (error) {
      console.error('Error re-ingesting:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (file.type !== 'text/plain') {
      alert("Only .txt files are allowed for evidence.");
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setMessages(prev => [...prev, { role: 'assistant', content: `Securely uploaded: ${file.name}. Detective is indexing it in the background.` }]);

      fetchCases();
      fetchTimeline();
    } catch (error) {
      console.error('Error uploading file:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: `Upload failed: ${error.message}` }]);
    } finally {
      setIsUploading(false);
      // Reset input so same file can be selected again if needed
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, { message: input });

      setMessages(prev => [...prev, { role: 'assistant', content: response.data.response }]);

      // Update Case Board with new sources
      setSources(prev => {
        const newSources = response.data.sources;
        const combined = [...newSources, ...prev];
        const unique = Array.from(new Set(combined.map(s => s.source)))
          .map(source => combined.find(s => s.source === source));
        return unique.slice(0, 9);
      });

      fetchTimeline();
    } catch (error) {
      console.error('Error calling API:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I lost my connection to the database. Is the API server running?' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="layout-root noir-theme">
      <div className="bg-mesh" />

      {/* Case Archive Sidebar */}
      <aside className="sidebar-archive glass">
        <div className="sidebar-header">
          <div className="brand-group">
            <div className="icon-box">
              <Clock className="accent-blue" size={20} />
            </div>
            <h2 className="brand-title">Archives</h2>
          </div>

          <button
            onClick={handleIngest}
            className="sync-btn"
          >
            <RefreshCw size={14} className={isLoading ? "spin" : ""} />
            Sync Evidence
          </button>

          <div style={{ marginTop: '8px' }}>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept=".txt"
              onChange={handleFileUpload}
            />
            <button
              onClick={() => fileInputRef.current.click()}
              className="sync-btn"
              style={{ borderColor: 'var(--accent-blue)', background: 'rgba(59, 130, 246, 0.1)' }}
            >
              <Upload size={14} className={isUploading ? "spin" : ""} />
              {isUploading ? 'Uploading...' : 'Upload Evidence'}
            </button>
          </div>
        </div>

        <div className="sidebar-content">
          <p className="section-label">Active Investigations</p>
          <div className="case-list">
            {['All', ...cases].map(caseName => (
              <button
                key={caseName}
                onClick={() => setSelectedCase(caseName)}
                className={`case-item ${selectedCase === caseName ? 'active' : ''}`}
              >
                <div className="case-dot" />
                <span className="case-name">{caseName}</span>
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* Main Board Area */}
      <main className="main-viewport">
        <header className="viewport-header">
          <div className="viewport-title-group">
            <div className="eyebrow">
              <span className="line" />
              Intelligence Dashboard
            </div>
            <h1 className="viewport-title">
              {activeView === 'board' ? 'The War Board' : 'Timeline Evidence'}
            </h1>
            <p className="viewport-subtitle">Viewing investigation: <span className="highlight">{selectedCase}</span></p>
          </div>

          <div className="view-selector">
            <button
              onClick={() => setActiveView('board')}
              className={`selector-btn ${activeView === 'board' ? 'active' : ''}`}
            >
              Board View
            </button>
            <button
              onClick={() => setActiveView('timeline')}
              className={`selector-btn ${activeView === 'timeline' ? 'active' : ''}`}
            >
              Historical
            </button>
            <button
              onClick={() => setActiveView('trace')}
              className={`selector-btn ${activeView === 'trace' ? 'active' : ''}`}
            >
              Trace
            </button>
          </div>
        </header>

        <div className="viewport-content">
          {activeView === 'board' ? (
            <div className="board-container">
              {sources.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">
                    <Search size={32} />
                  </div>
                  <p className="empty-title">No intelligence pinned.</p>
                  <p className="empty-desc">Initiate a query in the archive to populate the board.</p>
                </div>
              ) : (
                <div className="board-grid">
                  <AnimatePresence mode="popLayout">
                    {sources.map((src, i) => (
                      <motion.div
                        key={src.source}
                        layout
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        className="intel-card"
                      >
                        <div className="card-pin">
                          <Pin size={14} />
                        </div>

                        <div className="card-label">
                          <FileText size={12} />
                          {src.source.replace('.txt', '').replace(/_/g, ' ')}
                        </div>

                        <h3 className="card-heading">Intelligence Segment</h3>
                        <p className="card-body">
                          {src.content}
                        </p>

                        <div className="card-footer">
                          <span className="ref-code">REF: {Math.random().toString(36).substr(2, 6).toUpperCase()}</span>
                          <div className="deco-dots">
                            <div className="dot" />
                            <div className="dot" />
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              )}
            </div>
          ) : activeView === 'timeline' ? (
            <div className="timeline-view">
              {timeline.map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="timeline-row"
                >
                  <div className="time-col">
                    <span className="time-stamp">{item.time}</span>
                  </div>
                  <div className="node-col">
                    <div className="node-dot" />
                    <div className="node-line" />
                  </div>
                  <div className="detail-col">
                    <div className="timeline-card">
                      <p className="event-desc">{item.event}</p>
                      <div className="event-meta">
                        <Pin size={10} /> {item.source}
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="trace-container glass">
              <h3 className="trace-status">Network Analysis: {graphData.nodes.length} Nodes Active</h3>
              <div className="trace-graph">
                {/* SVG for Links - needs to be first to stay behind nodes */}
                <svg className="trace-links-svg">
                  {graphData.links.map((link, idx) => {
                    const sourceIdx = graphData.nodes.findIndex(n => n.id === link.source);
                    const targetIdx = graphData.nodes.findIndex(n => n.id === link.target);

                    if (sourceIdx === -1 || targetIdx === -1) return null;

                    const getPos = (index) => {
                      const node = graphData.nodes[index];
                      const isRoot = node.type === 'root';
                      const angle = (index / graphData.nodes.length) * 2 * Math.PI;
                      const x = isRoot ? 50 : 50 + (Math.cos(angle) * 35);
                      const y = isRoot ? 50 : 50 + (Math.sin(angle) * 35);
                      return { x, y };
                    };

                    const s = getPos(sourceIdx);
                    const t = getPos(targetIdx);

                    return (
                      <motion.line
                        key={`${link.source}-${link.target}-${idx}`}
                        x1={`${s.x}%`}
                        y1={`${s.y}%`}
                        x2={`${t.x}%`}
                        y2={`${t.y}%`}
                        initial={{ pathLength: 0, opacity: 0 }}
                        animate={{ pathLength: 1, opacity: 0.4 }}
                        transition={{ duration: 1, delay: idx * 0.05 }}
                        className="trace-link-line"
                      />
                    );
                  })}
                  {/* Decorative circles */}
                  <circle cx="50%" cy="50%" r="20%" className="trace-deco-ring" />
                  <circle cx="50%" cy="50%" r="35%" className="trace-deco-ring" />
                </svg>

                {graphData.nodes.map((node, i) => {
                  const isRoot = node.type === 'root';
                  const angle = (i / graphData.nodes.length) * 2 * Math.PI;
                  const x = isRoot ? 50 : 50 + (Math.cos(angle) * 35);
                  const y = isRoot ? 50 : 50 + (Math.sin(angle) * 35);

                  return (
                    <motion.div
                      key={node.id}
                      className={`trace-node ${node.type}`}
                      initial={{ opacity: 0, scale: 0 }}
                      animate={{ opacity: 1, scale: 1, left: `${x}%`, top: `${y}%` }}
                      transition={{ delay: i * 0.05 }}
                    >
                      <div className="node-icon">
                        {node.type === 'root' ? <Search size={16} /> :
                          node.type === 'file' ? <FileText size={12} /> : <Link2 size={12} />}
                      </div>
                      <span className="node-label">{node.label.replace('.txt', '')}</span>
                    </motion.div>
                  );
                })}
              </div>
              <div className="trace-overlay">
                <p>RELATIONSHIP MATRIX GENERATED // SYSTEM SECURE</p>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Chat Sidebar */}
      < aside className="sidebar-chat" >
        <header className="chat-header">
          <div className="detective-profile">
            <div className="profile-icon">
              <Cpu className="accent-blue" size={20} />
            </div>
            <div className="profile-info">
              <h2 className="profile-name">Detective Core</h2>
              <div className="status-indicator">
                <div className={`status-dot ${serverStatus}`} />
                <span className="status-label">{serverStatus}</span>
              </div>
            </div>
          </div>
        </header>

        <div className="chat-body" ref={scrollRef}>
          <AnimatePresence>
            {messages.map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: msg.role === 'user' ? 20 : -20 }}
                animate={{ opacity: 1, x: 0 }}
                className={`msg-wrapper ${msg.role}`}
              >
                <div className="msg-bubble">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {isLoading && (
            <div className="loading-state">
              <div className="dot-group">
                {[0, 1, 2].map(d => (
                  <motion.div
                    key={d}
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ repeat: Infinity, duration: 1, delay: d * 0.2 }}
                    className="loading-dot"
                  />
                ))}
              </div>
              Scanning intel...
            </div>
          )}
        </div>

        <footer className="chat-footer">
          <div className="input-group">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Query the database..."
              className="chat-input"
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="send-btn"
            >
              <Send size={16} />
            </button>
          </div>
          <p className="footer-tag">
            Confidential Evidence Analysis System v2.0
          </p>
        </footer>
      </aside >
    </div >
  );
}

export default App;
