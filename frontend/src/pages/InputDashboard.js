import axios from "axios";
import { React, useState, useEffect } from "react";

const BASE_URL = 'http://localhost:8000';
const MAX_CAPACITY = 500;
const MAX_POPULATION_SIZE = 500;
const MAX_GENERATIONS = 500;

function InputDashboard() {
    const [loading, setLoading] = useState(false);
    
    //let zones = [];
    const [zones, setZones] = useState([]); // doesn't work?
    const [selectedZone, setSelectedZone] = useState('');
    const [zonesToOptimize, setZonesToOptimize] = useState([]); // Max num of zones to optimize?

    const [id, setId] = useState(0); // How are the IDs determined? just increment 1 from last id on record?
    const [name, setName] = useState("");
    const [capacity, setCapacity] = useState(0);
    const [currentFee, setCurrentFee] = useState(0);
    const [currentOccupancy, setCurrentOccupancy] = useState(0);
    const [elasticity, setElasticity] = useState(0);
    const [minFee, setMinFee] = useState(0);
    const [maxFee, setMaxFee] = useState(0);

    const [populationSize, setPopulationSize] = useState(100);
    const [generations, setGenerations] = useState(40);
    const [goalOccupancy, setGoalOccupancy] = useState(0.85);

    useEffect(() => {
        loadZones();
    }, []);

    const loadZones = async () => {
        try {
            setLoading(true);
            const response = await axios.get(BASE_URL + '/zones');
            setZones(response.data); // why doesn't this work?? helloo?????

            //console.log(zones);
            //console.log(response.data) // why don't hese match????? and why are they printed twice??????
        }

        catch(err) {
            console.error("Error loading zones.", err);
        }

        finally {
            setLoading(false);
        }
    }

    function addToOptimizeList(zone) {
        zonesToOptimize.push(zone);
    }


    function DisplayOptimizedZones() {
        const removeZone = (zone) => {zonesToOptimize.splice(zonesToOptimize.indexOf(zone), 1)};

        return(
            <ul>
                {zonesToOptimize.map(zone => <li key={zone.id}>{zone.name}</li>)}
            </ul>
        )
    }

    function ZoneForm() {
        if (selectedZone) {
            return(
                <form>
                    <label htmlFor="zone-name">Name</label>
                    <input type="text" id="zone-name" onChange={(e) => setName(e.target.value)} value={name} required />

                    <label htmlFor="zone-capacity">Capacity</label>
                    <input type="number" id="zone-capacity" value={capacity} min="0" max={MAX_CAPACITY} required />

                    <label htmlFor="zone-current-fee">Current Fee</label>
                    <input type="number" id="zone-current-fee" value={currentFee} min="0" step="0.01" required />

                    <label htmlFor="zone-current-occupancy">Current Occupancy</label>
                    <input type="number"  id="zone-current-occupancy" value={currentOccupancy} min="0" max="1" step="0.01" required />

                    <label htmlFor="zone-elasticity">Elasticity</label>
                    <input type="number" id="zone-elasticity" min="0" step="0.01" />

                    <label htmlFor="zone-minimum-fee">Minimum Fee</label>
                    <input type="number" id="zone-minimum-fee" min="0" step="0.01" required />

                    <label htmlFor="zone-maximum-fee">Maximum Fee</label>
                    <input type="number" id="zone-maximum-fee" min={minFee} step="0.01" required />
                </form>
        )}
    }

    function handleForm(e) {
        setSelectedZone(e.target.value);
        setId(selectedZone.id);
        setName(selectedZone.name);
        setCapacity(selectedZone.capacity);
        setCurrentFee(selectedZone.currentFee);
        setCurrentOccupancy(selectedZone.currentOccupancy);
        setElasticity(selectedZone.elasticity);
        setMinFee(selectedZone.minFee);
        setMaxFee(selectedZone.maxFee);
    }

    function NewZone() {

    }

    function OptimizationSettings() {
        return(
            <form>
                <label htmlFor="pop-size">Population Size</label>
                <input type="number" id="pop-size" min="0" max={MAX_POPULATION_SIZE} placeholder={populationSize} />

                <label htmlFor="generations">Generations</label>
                <input type="number" id="generations" min="1" max={MAX_GENERATIONS} placeholder={generations} />

                <label htmlFor="target-occupancy">Target Occupancy</label>
                <input type="number" id="target-occupancy" min="0" max="1" step="0.01" placeholder={goalOccupancy} />
            </form>
        )
    }

    function handleSubmit(e) {
        console.log("Submitting.")
        e.preventDefault();
        zonesToOptimize.push(selectedZone);
        console.log(zonesToOptimize);
    }


    function ZoneDropDown() {
        return(
            <form onSubmit={handleSubmit}>
                <select id="zone-selection" value={selectedZone} onChange={handleForm}>
                    {zones.map(zone => (
                        <option key={zone.id} value={zone}>
                            {zone.name}
                        </option>
                ))}
                </select>

                <input type="submit" />
            </form>
        )
    }

    return(
        <div>
            <ZoneDropDown />
            <DisplayOptimizedZones />
            <ZoneForm />
            <OptimizationSettings />

            <button>Start Optimization</button>
        </div>
    )
}

export default InputDashboard;