"use client"

import { useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"
import { searchContracts } from "@/lib/actions"
import { ContractDetails } from "@/components/contract-details"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import type { ContractResult } from "@/lib/types"
import { Copy, ExternalLink, FileCode, Tag } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

export function ResultsList() {
  const searchParams = useSearchParams()
  const query = searchParams.get("q")
  const { toast } = useToast()

  const [results, setResults] = useState<ContractResult[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedContract, setSelectedContract] = useState<string | null>(null)
  const [contractDetails, setContractDetails] = useState<any | null>(null)
  const [loadingDetails, setLoadingDetails] = useState(false)

  useEffect(() => {
    async function fetchResults() {
      if (!query) return

      setLoading(true)
      try {
        const data = await searchContracts(query)
        setResults(data)
      } catch (error) {
        console.error("Error fetching results:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchResults()
  }, [query])

  const handleViewDetails = async (contractId: string) => {
    setSelectedContract(contractId)
    setLoadingDetails(true)

    try {
      // In a real app, this would fetch from the API
      const contract = results.find((r) => r.id === contractId)

      // Simulate API call delay
      await new Promise((resolve) => setTimeout(resolve, 500))

      setContractDetails({
        ...contract,
        fullCode: `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract ${contract?.name || "SmartContract"} is ERC721, Ownable {
    uint256 private _tokenIds;
    uint256 public mintPrice = 0.05 ether;
    uint256 public maxSupply = 10000;
    uint256 public maxPerWallet = 3;
    bool public isPublicMintEnabled = false;
    string internal baseTokenUri;
    mapping(address => uint256) public walletMints;

    constructor() ERC721("${contract?.name || "NFT Collection"}", "${contract?.symbol || "NFT"}") {
        // Initialize contract
    }

    function setIsPublicMintEnabled(bool _isPublicMintEnabled) external onlyOwner {
        isPublicMintEnabled = _isPublicMintEnabled;
    }

    function setBaseTokenUri(string calldata _baseTokenUri) external onlyOwner {
        baseTokenUri = _baseTokenUri;
    }

    function tokenURI(uint256 _tokenId) public view override returns (string memory) {
        require(_exists(_tokenId), "Token does not exist");
        return string(abi.encodePacked(baseTokenUri, Strings.toString(_tokenId), ".json"));
    }

    function mint(uint256 _quantity) public payable {
        require(isPublicMintEnabled, "Public mint is not enabled");
        require(msg.value == _quantity * mintPrice, "Wrong mint value");
        require(_tokenIds + _quantity <= maxSupply, "Sold out");
        require(walletMints[msg.sender] + _quantity <= maxPerWallet, "Exceed max wallet");

        for (uint256 i = 0; i < _quantity; i++) {
            uint256 newTokenId = _tokenIds + 1;
            _tokenIds++;
            _safeMint(msg.sender, newTokenId);
        }
    }

    function withdraw() external onlyOwner {
        (bool success, ) = payable(owner()).call{value: address(this).balance}("");
        require(success, "Withdraw failed");
    }
}`,
        abi: [
          {
            inputs: [],
            stateMutability: "nonpayable",
            type: "constructor",
          },
          {
            inputs: [
              {
                internalType: "uint256",
                name: "_quantity",
                type: "uint256",
              },
            ],
            name: "mint",
            outputs: [],
            stateMutability: "payable",
            type: "function",
          },
          {
            inputs: [
              {
                internalType: "bool",
                name: "_isPublicMintEnabled",
                type: "bool",
              },
            ],
            name: "setIsPublicMintEnabled",
            outputs: [],
            stateMutability: "nonpayable",
            type: "function",
          },
        ],
        deployments: [
          {
            network: "Ethereum Mainnet",
            address: "0x1234567890123456789012345678901234567890",
            timestamp: "2023-05-15T14:30:00Z",
          },
          {
            network: "Polygon",
            address: "0x0987654321098765432109876543210987654321",
            timestamp: "2023-06-02T09:15:00Z",
          },
        ],
      })
    } catch (error) {
      console.error("Error fetching contract details:", error)
    } finally {
      setLoadingDetails(false)
    }
  }

  if (!query) {
    return (
      <div className="text-center py-12">
        <FileCode className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">No search query</h3>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Enter a search term to find smart contracts</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold mb-4">Searching for: "{query}"</h2>
        {[1, 2, 3].map((i) => (
          <Card key={i} className="overflow-hidden">
            <CardHeader className="pb-2">
              <Skeleton className="h-6 w-1/3" />
              <Skeleton className="h-4 w-2/3" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-5/6" />
            </CardContent>
            <CardFooter>
              <Skeleton className="h-8 w-24" />
            </CardFooter>
          </Card>
        ))}
      </div>
    )
  }

  if (selectedContract && contractDetails) {
    return (
      <ContractDetails
        contract={contractDetails}
        onBack={() => {
          setSelectedContract(null)
          setContractDetails(null)
        }}
      />
    )
  }

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">
        {results.length} results for: "{query}"
      </h2>

      {results.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
          <FileCode className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">No results found</h3>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Try adjusting your search terms or try a different query
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {results.map((contract) => (
            <Card key={contract.id} className="overflow-hidden hover:shadow-md transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg">{contract.name}</CardTitle>
                    <CardDescription>{contract.description}</CardDescription>
                  </div>
                  <Badge variant={contract.verified ? "default" : "outline"}>
                    {contract.verified ? "Verified" : "Unverified"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2 mb-3">
                  {contract.tags.map((tag, i) => (
                    <Badge key={i} variant="secondary" className="flex items-center gap-1">
                      <Tag className="h-3 w-3" />
                      {tag}
                    </Badge>
                  ))}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  <div className="flex items-center gap-1">
                    <span className="font-medium">Platform:</span> {contract.platform}
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="font-medium">Language:</span> {contract.language}
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex flex-wrap gap-2">
                <Button
                  variant="default"
                  onClick={() => handleViewDetails(contract.id)}
                  disabled={loadingDetails && selectedContract === contract.id}
                >
                  {loadingDetails && selectedContract === contract.id ? (
                    <span className="flex items-center gap-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      Loading...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">View Details</span>
                  )}
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const address = contract.address || "0x1234567890123456789012345678901234567890"
                    navigator.clipboard.writeText(address)
                    toast({
                      title: "Address copied",
                      description: "Contract address copied to clipboard",
                    })
                  }}
                  className="flex items-center gap-1"
                >
                  <Copy className="h-3.5 w-3.5" />
                  Copy Address
                </Button>

                {contract.externalUrl && (
                  <Button variant="outline" size="icon" asChild className="ml-auto">
                    <a href={contract.externalUrl} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-4 w-4" />
                      <span className="sr-only">External link</span>
                    </a>
                  </Button>
                )}
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
