import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { SupplyChainData, OptimizationResults } from '../types';

interface FileUploadProps {
  onDataUpload: (data: SupplyChainData, results: OptimizationResults) => void;
  loading: boolean;
  setLoading: (loading: boolean) => void;
}

export default function FileUpload({ onDataUpload, loading, setLoading }: FileUploadProps) {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  


  const onDrop = useCallback((acceptedFiles: File[]) => {
    const excelFiles = acceptedFiles.filter(file => 
      file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
    );
    
    if (excelFiles.length !== acceptedFiles.length) {
      toast.error('Please upload only Excel files (.xlsx or .xls)');
      return;
    }

    setUploadedFiles(prev => [...prev, ...excelFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    multiple: true
  });

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
  if (uploadedFiles.length === 0) {
    toast.error('Please select files to upload');
    return;
  }

  setLoading(true);

  try {
    const formData = new FormData();
    for (const file of uploadedFiles) {
      // "files" name matches FastAPI: files: List[UploadFile] = File(...)
      formData.append("files", file);
    }

    const res = await fetch(`${import.meta.env.VITE_API_URL}/upload-files`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || "Upload failed");
    }

    const json = await res.json();

    const summary: SupplyChainData = {
      locations_count: json.data_summary?.locations ?? 0,
      warehouses_count: json.data_summary?.warehouses ?? 0,
      stores_count: json.data_summary?.stores ?? 0,
      time_periods: json.data_summary?.time_periods ?? 0,
      capacity_records: 0,
      demand_records: 0,
    };

    const results: OptimizationResults = {
      demand_forecast: json.results?.demand_forecast,
      allocation: json.results?.allocation,
      routing: json.results?.routing,
      metrics: json.results?.metrics,
    };

    toast.success('Files uploaded and processed successfully!');
    onDataUpload(summary, results);
    setUploadedFiles([]);

  } catch (error) {
    console.error('Upload error:', error);
    toast.error(error instanceof Error ? error.message : 'Upload failed');
  } finally {
    setLoading(false);
  }
};


  return (
    <div className="bg-white rounded-lg shadow-lg border-2 p-6" style={{ borderColor: '#2C3E50' }}>
      <div className="text-center mb-6">
        <div className="p-3 rounded-full inline-block mb-3" style={{ backgroundColor: '#ECF0F1' }}>
          <Upload className="h-12 w-12" style={{ color: '#2C3E50' }} />
        </div>
        <h2 className="text-2xl font-bold mb-3" style={{ color: '#2C3E50' }}>
          Upload Supply Chain Data
        </h2>
        <p className="text-base" style={{ color: '#2C3E50' }}>
          Upload Excel files to begin optimization analysis
        </p>
      </div>

      <div
        {...getRootProps()}
        className={`border-3 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-300 ${
          isDragActive
            ? 'border-opacity-100 bg-opacity-10'
            : 'border-opacity-50 hover:border-opacity-75'
        }`}
        style={{ 
          borderColor: isDragActive ? '#16A085' : '#2C3E50',
          backgroundColor: isDragActive ? '#16A085' : 'transparent'
        }}
      >
        <input {...getInputProps()} />
        <FileText className="mx-auto h-10 w-10 mb-3" style={{ color: '#2C3E50' }} />
        {isDragActive ? (
          <p className="text-lg font-medium" style={{ color: '#16A085' }}>
            Drop the Excel files here...
          </p>
        ) : (
          <div>
            <p className="text-lg font-medium mb-2" style={{ color: '#2C3E50' }}>
              Drag & drop Excel files here, or click to select
            </p>
            <p className="text-sm" style={{ color: '#2C3E50' }}>
              Supports .xlsx and .xls files
            </p>
          </div>
        )}
      </div>

      {uploadedFiles.length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-bold mb-3" style={{ color: '#2C3E50' }}>
            Selected Files ({uploadedFiles.length})
          </h3>
          <div className="space-y-2">
            {uploadedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 rounded-lg border"
                style={{ backgroundColor: '#ECF0F1', borderColor: '#2C3E50' }}
              >
                <div className="flex items-center">
                  <FileText className="h-4 w-4 mr-3" style={{ color: '#2C3E50' }} />
                  <div>
                    <span className="font-medium text-sm" style={{ color: '#2C3E50' }}>{file.name}</span>
                    <span className="text-xs ml-2" style={{ color: '#2C3E50' }}>
                      ({(file.size / 1024).toFixed(1)} KB)
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  className="px-2 py-1 rounded text-sm font-medium hover:opacity-80 transition-opacity"
                  style={{ backgroundColor: '#C0392B', color: 'white' }}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-3 mt-6">
        <button
          onClick={handleUpload}
          disabled={uploadedFiles.length === 0 || loading}
          className="flex-1 py-3 px-4 rounded-lg text-base font-bold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ 
            backgroundColor: uploadedFiles.length === 0 || loading ? '#95A5A6' : '#E67E22',
            color: 'white'
          }}
        >
          {loading ? (
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Processing...
            </div>
          ) : (
            'Upload & Process Files'
          )}
        </button>
        
      </div>
    </div>
  );
}
