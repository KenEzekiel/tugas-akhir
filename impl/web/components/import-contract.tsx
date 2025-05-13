"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Copy, Check, Download, Package } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface ImportContractProps {
  contract: {
    name: string
    address: string
    abi: any[]
    platform: string
  }
}

export function ImportContract({ contract }: ImportContractProps) {
  const [open, setOpen] = useState(false)
  const [activeTab, setActiveTab] = useState("hardhat")
  const [copied, setCopied] = useState<Record<string, boolean>>({})
  const { toast } = useToast()

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopied({ ...copied, [key]: true })

    toast({
      title: "Copied to clipboard",
      description: "The code snippet has been copied to your clipboard",
    })

    setTimeout(() => {
      setCopied({ ...copied, [key]: false })
    }, 2000)
  }

  const hardhatSnippet = `// Import the contract in your Hardhat project
const { ethers } = require("hardhat");

async function main() {
  // Get the contract at the deployed address
  const ${contract.name.replace(/\s+/g, "")} = await ethers.getContractAt(
    "${contract.name}",
    "${contract.address}"
  );

  // Now you can interact with the contract
  // Example: const balance = await ${contract.name.replace(/\s+/g, "")}.balanceOf(address);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });`

  const truffleSnippet = `// Import the contract in your Truffle project
const ${contract.name.replace(/\s+/g, "")} = artifacts.require("${contract.name}");

module.exports = async function(callback) {
  try {
    // Get the deployed contract instance
    const instance = await ${contract.name.replace(/\s+/g, "")}.at("${contract.address}");
    
    // Now you can interact with the contract
    // Example: const balance = await instance.balanceOf(address);
    
    callback();
  } catch(error) {
    console.error(error);
    callback(error);
  }
};`

  const foundrySnippet = `// In your Foundry script or test
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Script.sol";
import "forge-std/console.sol";

interface I${contract.name.replace(/\s+/g, "")} {
    // Define the interface methods you need
    // Example: function balanceOf(address) external view returns (uint256);
}

contract Script${contract.name.replace(/\s+/g, "")}Interaction is Script {
    function run() external {
        // Use the existing deployment
        I${contract.name.replace(/\s+/g, "")} instance = I${contract.name.replace(/\s+/g, "")}(${contract.address});
        
        // Now you can interact with the contract
        // Example: uint256 balance = instance.balanceOf(address);
    }
}`

  const ethersSnippet = `// Using ethers.js in a JavaScript/TypeScript project
import { ethers } from "ethers";

// ABI - you'll need the contract ABI
const abi = ${JSON.stringify(contract.abi, null, 2)};

async function interactWithContract() {
  // Connect to the Ethereum network
  const provider = new ethers.providers.Web3Provider(window.ethereum);
  await provider.send("eth_requestAccounts", []);
  const signer = provider.getSigner();
  
  // Create a contract instance
  const contractAddress = "${contract.address}";
  const contract = new ethers.Contract(contractAddress, abi, signer);
  
  // Now you can call contract methods
  // Example: const balance = await contract.balanceOf(address);
}`

  const web3jsSnippet = `// Using web3.js in a JavaScript/TypeScript project
import Web3 from 'web3';

// ABI - you'll need the contract ABI
const abi = ${JSON.stringify(contract.abi, null, 2)};

async function interactWithContract() {
  // Connect to the Ethereum network
  const web3 = new Web3(window.ethereum);
  await window.ethereum.enable();
  
  // Create a contract instance
  const contractAddress = "${contract.address}";
  const contract = new web3.eth.Contract(abi, contractAddress);
  
  // Now you can call contract methods
  // Example: const balance = await contract.methods.balanceOf(address).call();
}`

  const npmPackageJson = `{
  "dependencies": {
    "@${contract.name.toLowerCase().replace(/\s+/g, "-")}/contracts": "^1.0.0"
  }
}`

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="flex items-center gap-2">
          <Package className="h-4 w-4" />
          Import Contract
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Import {contract.name}</DialogTitle>
          <DialogDescription>Choose your preferred method to import this contract into your project.</DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full mt-4">
          <TabsList className="grid grid-cols-3 mb-4">
            <TabsTrigger value="hardhat">Hardhat</TabsTrigger>
            <TabsTrigger value="truffle">Truffle</TabsTrigger>
            <TabsTrigger value="foundry">Foundry</TabsTrigger>
          </TabsList>

          <TabsContent value="hardhat">
            <Card className="overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Import with Hardhat</CardTitle>
                <CardDescription>
                  Use this code to interact with the deployed contract in your Hardhat project.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="relative">
                  <pre className="p-4 bg-gray-50 dark:bg-gray-800 rounded-md overflow-x-auto text-sm font-mono whitespace-pre-wrap break-words">
                    {hardhatSnippet}
                  </pre>
                  <Button
                    variant="outline"
                    size="sm"
                    className="absolute top-2 right-2"
                    onClick={() => copyToClipboard(hardhatSnippet, "hardhat")}
                  >
                    {copied["hardhat"] ? (
                      <span className="flex items-center gap-1">
                        <Check className="h-4 w-4" />
                        Copied
                      </span>
                    ) : (
                      <span className="flex items-center gap-1">
                        <Copy className="h-4 w-4" />
                        Copy
                      </span>
                    )}
                  </Button>
                </div>
              </CardContent>
              <CardFooter>
                <Button variant="outline" className="flex items-center gap-2" asChild>
                  <a
                    href={`data:text/javascript;charset=utf-8,${encodeURIComponent(hardhatSnippet)}`}
                    download={`${contract.name.replace(/\s+/g, "")}_hardhat.js`}
                  >
                    <Download className="h-4 w-4" />
                    Download Script
                  </a>
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>

          <TabsContent value="truffle">
            <Card className="overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Import with Truffle</CardTitle>
                <CardDescription>
                  Use this code to interact with the deployed contract in your Truffle project.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="relative">
                  <pre className="p-4 bg-gray-50 dark:bg-gray-800 rounded-md overflow-x-auto text-sm font-mono whitespace-pre-wrap break-words">
                    {truffleSnippet}
                  </pre>
                  <Button
                    variant="outline"
                    size="sm"
                    className="absolute top-2 right-2"
                    onClick={() => copyToClipboard(truffleSnippet, "truffle")}
                  >
                    {copied["truffle"] ? (
                      <span className="flex items-center gap-1">
                        <Check className="h-4 w-4" />
                        Copied
                      </span>
                    ) : (
                      <span className="flex items-center gap-1">
                        <Copy className="h-4 w-4" />
                        Copy
                      </span>
                    )}
                  </Button>
                </div>
              </CardContent>
              <CardFooter>
                <Button variant="outline" className="flex items-center gap-2" asChild>
                  <a
                    href={`data:text/javascript;charset=utf-8,${encodeURIComponent(truffleSnippet)}`}
                    download={`${contract.name.replace(/\s+/g, "")}_truffle.js`}
                  >
                    <Download className="h-4 w-4" />
                    Download Script
                  </a>
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>

          <TabsContent value="foundry">
            <Card className="overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Import with Foundry</CardTitle>
                <CardDescription>
                  Use this code to interact with the deployed contract in your Foundry project.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="relative">
                  <pre className="p-4 bg-gray-50 dark:bg-gray-800 rounded-md overflow-x-auto text-sm font-mono whitespace-pre-wrap break-words">
                    {foundrySnippet}
                  </pre>
                  <Button
                    variant="outline"
                    size="sm"
                    className="absolute top-2 right-2"
                    onClick={() => copyToClipboard(foundrySnippet, "foundry")}
                  >
                    {copied["foundry"] ? (
                      <span className="flex items-center gap-1">
                        <Check className="h-4 w-4" />
                        Copied
                      </span>
                    ) : (
                      <span className="flex items-center gap-1">
                        <Copy className="h-4 w-4" />
                        Copy
                      </span>
                    )}
                  </Button>
                </div>
              </CardContent>
              <CardFooter>
                <Button variant="outline" className="flex items-center gap-2" asChild>
                  <a
                    href={`data:text/plain;charset=utf-8,${encodeURIComponent(foundrySnippet)}`}
                    download={`${contract.name.replace(/\s+/g, "")}_foundry.sol`}
                  >
                    <Download className="h-4 w-4" />
                    Download Script
                  </a>
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>
        </Tabs>

        <div className="mt-6">
          <h3 className="text-lg font-medium mb-2">JavaScript Libraries</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">ethers.js</CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="relative">
                  <Button
                    variant="outline"
                    size="sm"
                    className="absolute top-2 right-2 z-10"
                    onClick={() => copyToClipboard(ethersSnippet, "ethers")}
                  >
                    {copied["ethers"] ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                  </Button>
                  <pre className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md overflow-x-auto text-xs font-mono max-h-40 whitespace-pre-wrap break-words">
                    {ethersSnippet}
                  </pre>
                </div>
              </CardContent>
            </Card>

            <Card className="overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">web3.js</CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="relative">
                  <Button
                    variant="outline"
                    size="sm"
                    className="absolute top-2 right-2 z-10"
                    onClick={() => copyToClipboard(web3jsSnippet, "web3")}
                  >
                    {copied["web3"] ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                  </Button>
                  <pre className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md overflow-x-auto text-xs font-mono max-h-40 whitespace-pre-wrap break-words">
                    {web3jsSnippet}
                  </pre>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="mt-6">
          <h3 className="text-lg font-medium mb-2">Contract ABI</h3>
          <Card className="overflow-hidden">
            <CardHeader className="pb-2">
              <div className="flex justify-between items-center">
                <CardTitle className="text-sm">ABI JSON</CardTitle>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => copyToClipboard(JSON.stringify(contract.abi, null, 2), "abi")}
                  >
                    {copied["abi"] ? (
                      <span className="flex items-center gap-1">
                        <Check className="h-3 w-3" />
                        Copied
                      </span>
                    ) : (
                      <span className="flex items-center gap-1">
                        <Copy className="h-3 w-3" />
                        Copy ABI
                      </span>
                    )}
                  </Button>
                  <Button variant="outline" size="sm" asChild>
                    <a
                      href={`data:application/json;charset=utf-8,${encodeURIComponent(
                        JSON.stringify(contract.abi, null, 2),
                      )}`}
                      download={`${contract.name.replace(/\s+/g, "")}_abi.json`}
                    >
                      <Download className="h-3 w-3" />
                    </a>
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <pre className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md overflow-x-auto text-xs font-mono max-h-40 whitespace-pre-wrap break-words">
                {JSON.stringify(contract.abi, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  )
}
