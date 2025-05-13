"use client"

import type React from "react"

import { useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { SearchIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useToast } from "@/hooks/use-toast"

export function Search() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { toast } = useToast()
  const [query, setQuery] = useState(searchParams.get("q") || "")
  const [isSearching, setIsSearching] = useState(false)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!query.trim()) {
      toast({
        title: "Empty query",
        description: "Please enter a search term",
        variant: "destructive",
      })
      return
    }

    setIsSearching(true)

    try {
      // Update URL with search query
      const params = new URLSearchParams(searchParams)
      params.set("q", query)
      router.push(`/?${params.toString()}`)
    } catch (error) {
      toast({
        title: "Search failed",
        description: "There was an error processing your search",
        variant: "destructive",
      })
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <form onSubmit={handleSearch} className="w-full max-w-3xl mx-auto">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Input
            type="text"
            placeholder="Search smart contracts using natural language..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full pl-4 pr-10 py-6 text-base rounded-lg border border-gray-300 dark:border-gray-700 focus:ring-2 focus:ring-primary"
          />
        </div>
        <Button type="submit" disabled={isSearching} className="px-6 py-6">
          {isSearching ? (
            <span className="flex items-center gap-2">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              Searching...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <SearchIcon className="h-4 w-4" />
              Search
            </span>
          )}
        </Button>
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
        Try: "Find Ethereum NFT contracts with royalty features" or "Show me DeFi lending protocols"
      </p>
    </form>
  )
}
