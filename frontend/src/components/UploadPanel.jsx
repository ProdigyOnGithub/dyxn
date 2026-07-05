import { useState, useRef } from 'react';
import api from '../api/client';
import toast from 'react-hot-toast';

export default function UploadPanel() {
  const [activeTab, setActiveTab] = useState('textbook');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState(null); // { type: 'success'|'error', message: '' }
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  const tabs = [
    { id: 'textbook', label: '📚 Textbook', accept: '.pdf,.docx,.txt' },
    { id: 'slides', label: '📊 Slides', accept: '.pdf,.pptx,.ppt' },
  ];

  const handleUpload = async (file) => {
    if (!file) return;

    setUploading(true);
    setProgress(0);
    setUploadStatus(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setProgress(pct);
        },
      });

      setUploadStatus({
        type: 'success',
        message: `✓ ${response.data.filename} uploaded successfully`,
      });
      toast.success(`${activeTab === 'textbook' ? '📚' : '📊'} ${file.name} uploaded!`);
    } catch (error) {
      const errMsg = error.response?.data?.detail || 'Upload failed';
      setUploadStatus({ type: 'error', message: errMsg });
      toast.error(`Upload failed: ${errMsg}`);
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUpload(file);
  };

  const currentTab = tabs.find((t) => t.id === activeTab);

  return (
    <div className="upload-section">
      <div className="upload-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`upload-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => {
              setActiveTab(tab.id);
              setUploadStatus(null);
              setProgress(0);
            }}
            id={`upload-tab-${tab.id}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div
        className={`upload-dropzone ${dragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        id={`upload-dropzone-${activeTab}`}
      >
        <div className="upload-dropzone-icon">
          {activeTab === 'textbook' ? '📚' : '📊'}
        </div>
        <div className="upload-dropzone-text">
          Drop your {activeTab} here or <strong>browse</strong>
        </div>
        <div className="upload-dropzone-hint">
          {currentTab?.accept.split(',').join(', ')}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept={currentTab?.accept}
          onChange={handleFileChange}
          disabled={uploading}
        />
      </div>

      {uploading && (
        <div className="upload-progress">
          <div className="upload-progress-bar-track">
            <div
              className="upload-progress-bar-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="upload-status">
            Uploading... {progress}%
          </div>
        </div>
      )}

      {uploadStatus && !uploading && (
        <div className={`upload-status ${uploadStatus.type}`}>
          {uploadStatus.message}
        </div>
      )}
    </div>
  );
}
