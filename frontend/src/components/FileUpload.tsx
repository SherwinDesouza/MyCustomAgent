import { useState, useRef } from 'react';
import './FileUpload.css';

interface FileUploadProps {
    onUploadSuccess: (files: any[]) => void;
    sessionId: string;
}

function FileUpload({ onUploadSuccess, sessionId }: FileUploadProps) {
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        setIsUploading(true);

        try {
            const formData = new FormData();
            Array.from(files).forEach(file => {
                formData.append('files', file);
            });
            formData.append('session_id', sessionId);

            const response = await fetch('http://localhost:8000/upload', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const result = await response.json();
            onUploadSuccess(result.files);

            // Reset file input
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        } catch (error) {
            console.error('Upload error:', error);
            alert('Failed to upload files. Please try again.');
        } finally {
            setIsUploading(false);
        }
    };

    const handleButtonClick = () => {
        fileInputRef.current?.click();
    };

    return (
        <div className="file-upload">
            <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="audio/*,image/*,.csv,.xls,.xlsx"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
            />
            <button
                className="upload-button"
                onClick={handleButtonClick}
                disabled={isUploading}
                title="Upload files"
            >
                {isUploading ? (
                    <svg className="spinner" width="24" height="24" viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none" opacity="0.25" />
                        <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" />
                    </svg>
                ) : (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                )}
            </button>
        </div>
    );
}

export default FileUpload;
