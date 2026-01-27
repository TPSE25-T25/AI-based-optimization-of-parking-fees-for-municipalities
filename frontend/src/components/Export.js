import {useState} from 'react';
import axios from 'axios';

// only zones to be exported? what about optimization settings?
// currently get(/zones) returns a list of zones which I assume will later return a .json file?

const BASE_URL = 'http://localhost:8000';
const LOCATION = '/zones';
//const DOWNLOAD_URL = '';

function Export() {
    const [exportedData, setExportedData] = useState(null);

    const fetchData = async () => {
        await axios.get(BASE_URL + LOCATION)
        .then(response => {
            console.log(response.data);
            setExportedData(response.data);});

        //DOWNLOAD_URL = URL.createObjectURL(exportedData);
        //document.getElementById("hidden-export-handler")?.click();
    }

    return(
        <div>
            <a id="hidden-export-handler" style={{display:"none"}}  download></a>
            <button id="export-btn" onClick={fetchData}>Export</button>
        </div>
    )
}

export default Export;