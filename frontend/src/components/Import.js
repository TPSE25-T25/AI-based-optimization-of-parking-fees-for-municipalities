import {useState} from 'react';
import axios from 'axios';

const BASE_URL = 'http://localhost:8000';
const LOCATION = '/zones' // Where to send this data exactly? can't post to /zones

function Import() {
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const [isUploading, setUploadStatus] = useState(false);

  const handleImport = async (e) => {
    setFile(e.target.files[0]);
    const formData = new FormData();
    formData.append("file", file);
    console.log(formData);

    try {
      const response = await axios.post(BASE_URL + LOCATION, formData);
    }
    catch(err) {
      console.error("Failed to import.", err);
    }
  }

  return(
    <div>
      <input type="file" id="hidden-import-handler" accept='.json' style={{display:"none"}} onChange={(e) => handleImport(e)}/>
      <button className='ImportButton' onClick={() => document.getElementById("hidden-import-handler")?.click()}>Import</button>
    </div>
  );
}

export default Import;