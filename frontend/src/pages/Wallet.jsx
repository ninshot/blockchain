import React from "react";
import { useState, useEffect } from "react";
import { createWallet} from "../services/api";


const Wallet = () => {
    const [loading, setLoading] = useState(true);
    const [keys, setKeys] = useState(null);
    const [error, setError] = useState('');

    useEffect(() => {
        setLoading(false);
    }, [keys]);
   

    const handleCreate = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setKeys(null);
        
        try{
            const result = await createWallet();
            if(result.status === "success" && result.data) {
                console.log("Wallet created successfully:", result.data.data);
                const {publicKey, privateKey} = result.data.data;
                setKeys({publicKey,privateKey});
            }
            else{
                setError("Failed to create wallet. Please try again.");
                setKeys(null);
            }
        } catch (err) {
            setError("Failed to create wallet. Please try again.");
            setKeys(null);
        }finally {
            setLoading(false);
        }
    }
   
    return(
        <div className="flex flex-col items-center justify-center min-h-screen bg-black ">
            <button 
                onClick={handleCreate}
                className="
                px-5 py-2.5 
                bg-black 
                text-white 
                text-[17px] 
                font-bold 
                uppercase 
                tracking-widest 
                rounded-none
                border-2
                border-yellow-300
                transition-shadow 
                duration-500
                shadow-[0_0_5px_rgb(0,0,0),0_0_25px_rgb(0,0,0),0_0_40px_rgb(0,0,0),0_0_100px_rgb(0,0,0)]
                hover:bg-yellow-300
                hover:text-black
                hover:shadow-[0_0_5px_rgb(245,158,11),0_0_10px_rgb(245,158,11),0_0_30px_rgb(245,158,11),0_0_50px_rgb(245,158,11)]
                ">
                {loading? "Generating..." : "Generate Wallet"}
            </button>
    
        {keys && (
            <div>
               <textarea readOnly className="w-300 h-40 mt-5 text-center bg-black border-2 border-yellow-300" 
                value={`Public Key: ${keys.publicKey}`}
                rows="4">
                    
                </textarea>
            </div>)}      
        </div>
    )

}

export default Wallet;