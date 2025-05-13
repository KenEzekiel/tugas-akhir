"use client"

import { useState } from "react"
import { Copy, Check, ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useToast } from "@/hooks/use-toast"

interface AddressBadgeProps {
  address: string
  network?: string
  explorerUrl?: string
}

export function AddressBadge({ address, network = "Ethereum", explorerUrl }: AddressBadgeProps) {
  const [copied, setCopied] = useState(false)
  const { toast } = useToast()

  const copyToClipboard = () => {
    navigator.clipboard.writeText(address)
    setCopied(true)

    toast({
      title: "Address copied",
      description: "Contract address copied to clipboard",
    })

    setTimeout(() => setCopied(false), 2000)
  }

  // Format address to show first 6 and last 4 characters
  const formatAddress = (addr: string) => {
    if (!addr) return ""
    return `${addr.substring(0, 6)}...${addr.substring(addr.length - 4)}`
  }

  // Determine explorer URL based on network
  const getExplorerUrl = () => {
    if (explorerUrl) return explorerUrl

    const networkLower = network.toLowerCase()
    if (networkLower.includes("ethereum") || networkLower === "mainnet") {
      return `https://etherscan.io/address/${address}`
    } else if (networkLower.includes("polygon")) {
      return `https://polygonscan.com/address/${address}`
    } else if (networkLower.includes("arbitrum")) {
      return `https://arbiscan.io/address/${address}`
    } else if (networkLower.includes("optimism")) {
      return `https://optimistic.etherscan.io/address/${address}`
    } else if (networkLower.includes("bsc") || networkLower.includes("binance")) {
      return `https://bscscan.com/address/${address}`
    } else if (networkLower.includes("avalanche")) {
      return `https://snowtrace.io/address/${address}`
    } else {
      return `https://etherscan.io/address/${address}`
    }
  }

  return (
    <div className="inline-flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-md px-2 py-1 text-sm font-mono">
      <span className="text-gray-500 dark:text-gray-400">{formatAddress(address)}</span>

      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={copyToClipboard}>
        {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
        <span className="sr-only">Copy address</span>
      </Button>

      <Button variant="ghost" size="icon" className="h-6 w-6" asChild>
        <a href={getExplorerUrl()} target="_blank" rel="noopener noreferrer">
          <ExternalLink className="h-3 w-3" />
          <span className="sr-only">View on explorer</span>
        </a>
      </Button>
    </div>
  )
}
