"use server"

import type { ContractResult } from "@/lib/types"

// Mock data for demonstration purposes
const mockContracts: ContractResult[] = [
  {
    id: "1",
    name: "CryptoKitties",
    symbol: "CK",
    description: "A popular NFT game that allows users to collect and breed digital cats",
    platform: "Ethereum",
    language: "Solidity",
    license: "MIT",
    created: "November 28, 2017",
    verified: true,
    tags: ["NFT", "Gaming", "ERC721"],
    externalUrl: "https://www.cryptokitties.co/",
    address: "0x06012c8cf97BEaD5deAe237070F9587f8E7A266d",
  },
  {
    id: "2",
    name: "Uniswap V3",
    symbol: "UNI",
    description: "Decentralized trading protocol for automated liquidity provision",
    platform: "Ethereum",
    language: "Solidity",
    license: "GPL-2.0",
    created: "May 5, 2021",
    verified: true,
    tags: ["DeFi", "DEX", "AMM", "ERC20"],
    externalUrl: "https://uniswap.org/",
    address: "0x1F98431c8aD98523631AE4a59f267346ea31F984",
  },
  {
    id: "3",
    name: "Aave V3",
    symbol: "AAVE",
    description:
      "Decentralized non-custodial liquidity protocol where users can participate as depositors or borrowers",
    platform: "Ethereum",
    language: "Solidity",
    license: "BUSL-1.1",
    created: "March 16, 2022",
    verified: true,
    tags: ["DeFi", "Lending", "ERC20"],
    externalUrl: "https://aave.com/",
    address: "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9",
  },
  {
    id: "4",
    name: "OpenSea Shared Storefront",
    symbol: "OPENSTORE",
    description: "A shared contract for creators to mint and sell NFTs without deploying their own contract",
    platform: "Ethereum",
    language: "Solidity",
    license: "MIT",
    created: "July 12, 2021",
    verified: true,
    tags: ["NFT", "Marketplace", "ERC1155"],
    externalUrl: "https://opensea.io/",
    address: "0x495f947276749Ce646f68AC8c4c6A248Bc53386",
  },
  {
    id: "5",
    name: "Chainlink Price Feed",
    symbol: "LINK",
    description:
      "Decentralized oracle network that provides reliable, tamper-proof inputs and outputs for complex smart contracts",
    platform: "Ethereum",
    language: "Solidity",
    license: "MIT",
    created: "January 1, 2019",
    verified: true,
    tags: ["Oracle", "Data Feed", "Infrastructure"],
    externalUrl: "https://chain.link/",
    address: "0x47e9cc84a99ef57937e5ca937252d93f1e52a86e",
  },
  {
    id: "6",
    name: "Compound Finance",
    symbol: "COMP",
    description: "Algorithmic, autonomous interest rate protocol built for developers",
    platform: "Ethereum",
    language: "Solidity",
    license: "BSD-3",
    created: "May 7, 2018",
    verified: true,
    tags: ["DeFi", "Lending", "Interest", "ERC20"],
    externalUrl: "https://compound.finance/",
    address: "0xc00e94cb662c3520282e6f5717214004a7f26888",
  },
  {
    id: "7",
    name: "ENS (Ethereum Name Service)",
    symbol: "ENS",
    description: "Distributed, open, and extensible naming system based on the Ethereum blockchain",
    platform: "Ethereum",
    language: "Solidity",
    license: "MIT",
    created: "May 4, 2017",
    verified: true,
    tags: ["Domain Names", "Identity", "Infrastructure"],
    externalUrl: "https://ens.domains/",
    address: "0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85",
  },
]

export async function searchContracts(query: string): Promise<ContractResult[]> {
  // In a real application, this would call an API or database
  // For demonstration, we'll return mock data with a delay to simulate network request
  await new Promise((resolve) => setTimeout(resolve, 1500))

  // Simple filtering based on the query
  // In a real app, this would be handled by a backend search engine
  const lowercaseQuery = query.toLowerCase()

  return mockContracts.filter((contract) => {
    return (
      contract.name.toLowerCase().includes(lowercaseQuery) ||
      contract.description.toLowerCase().includes(lowercaseQuery) ||
      contract.tags.some((tag) => tag.toLowerCase().includes(lowercaseQuery)) ||
      contract.platform.toLowerCase().includes(lowercaseQuery)
    )
  })
}
