import React, { useState } from 'react';
import axios from 'axios';
//import ExportConfiguration from "./ImportExport";

const BASE_URL = 'http://localhost:8000';
const MAX_POPULATION_SIZE = 500;
const MAX_GENERATIONS = 500;
    
export default function OptimizationSettings({handleSubmit, generations, setGenerations, populationSize, setPopulationSize, targetOccupancy, setTargetOccupancy}) {
    const importConfig = (e) => {
        //e.preventDefault();

        try {
            console.log(e.target.files[0]);
            const reader = new FileReader();
            reader.readAsText(e.target.files[0]);

            reader.onload = () => {
                const data = JSON.parse(reader.result);
                console.log(data);

                setPopulationSize(data.population_size);
                setGenerations(data.generations);
                setTargetOccupancy(data.target_occupancy);
            };

        }
        catch(error) {
            console.error("Failed to import, please make sure you've selected a valid file.", error);
        }
        
    };

    
    const exportConfig = ({}) => {
        try {
            const importedSettings = {
                "population_size" : populationSize,
                "generations" : generations,
                "target_occupancy" : targetOccupancy
            };

            const fileName = "optimization_settings";

            //setDownloadStatus(true);
            //const response = await axios.get(''); // where to get config? or just read it off the form?
            const configData = new Blob([JSON.stringify(importedSettings)], {type: 'application/json'});
            const downloadURL = URL.createObjectURL(configData);
            const downloadLink = document.createElement('a');
            downloadLink.href = downloadURL;
            downloadLink.download = `${fileName}.json`;
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
        }
        catch (error) {
            console.error("Failed to export.", error);
        }
        finally{
            //setDownloadStatus(false);
        }
    };


    return(
        <div>
            <form id="settings-form" onSubmit={handleSubmit}>
                <label htmlFor="pop-size">Population Size</label>
                <input type="number" id="pop-size" min="0" max={MAX_POPULATION_SIZE} onChange={(e) => setPopulationSize(e.target.value)} value={populationSize} />

                <label htmlFor="generations">Generations</label>
                <input type="number" id="generations" min="1" max={MAX_GENERATIONS} onChange={(e) => setGenerations(e.target.value)} value={generations} />

                <label htmlFor="target-occupancy">Target Occupancy</label>
                <input type="number" id="target-occupancy" min="0" max="1" step="0.01" onChange={(e) => setTargetOccupancy(e.target.value)} value={targetOccupancy} />
            </form>

            <button onClick={exportConfig}>Export Configuration</button>
            
            <input type="file" id="hidden-import-handler" accept='.json' style={{display:"none"}} onChange={importConfig}/>
            <button className='ImportButton' onClick={() => document.getElementById("hidden-import-handler")?.click()}>Import Configuration</button>
        </div>
    )
}
