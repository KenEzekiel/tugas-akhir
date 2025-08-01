"use client";

import type React from "react";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  SearchIcon,
  WandSparklesIcon,
  SlidersHorizontal,
  Code,
  FileText,
  Brain,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useToast } from "@/hooks/use-toast";
import type { SearchType } from "@/lib/types";

interface RefineResponse {
  original_query: string;
  refined_query: string;
  reasoning?: string;
}

const searchTypeConfig = {
  vector: {
    label: "Vector Search",
    description: "Semantic similarity using AI embeddings",
    icon: Brain,
    placeholder: "Find contracts by natural language...",
    examples:
      "Try: 'Find Ethereum NFT contracts with royalty features' or 'Show me DeFi lending protocols'",
  },
  text: {
    label: "Text Search",
    description: "Search across all contract metadata",
    icon: FileText,
    placeholder: "Search contract names, descriptions, standards...",
    examples: "Try: 'ERC20' or 'DeFi lending' or 'NFT marketplace'",
  },
  source_code: {
    label: "Source Code Search",
    description: "Search in contract names and source code",
    icon: Code,
    placeholder: "Search function names, variables, code patterns...",
    examples: "Try: 'transfer' or 'mint' or 'approve' or 'balanceOf'",
  },
};

export function Search() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const [query, setQuery] = useState(searchParams.get("q") || "");
  const [searchType, setSearchType] = useState<SearchType>(
    (searchParams.get("type") as SearchType) || "vector"
  );
  const [isSearching, setIsSearching] = useState(false);
  const [isRefining, setIsRefining] = useState(false);

  const currentConfig = searchTypeConfig[searchType];

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!query.trim()) {
      toast({
        title: "Empty query",
        description: "Please enter a search term",
        variant: "destructive",
      });
      return;
    }

    setIsSearching(true);

    try {
      // Update URL with search query and search type
      const params = new URLSearchParams(searchParams);
      params.set("q", query);
      params.set("type", searchType);
      router.push(`/?${params.toString()}`);
    } catch (error) {
      toast({
        title: "Search failed",
        description: "There was an error processing your search",
        variant: "destructive",
      });
    } finally {
      setIsSearching(false);
    }
  };

  const handleRefine = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!query.trim()) {
      toast({
        title: "Empty query",
        description: "Please enter a search term to refine",
        variant: "destructive",
      });
      return;
    }

    setIsRefining(true);

    try {
      // Call the refine API endpoint
      const response = await fetch("http://localhost:8000/refine", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const refineResult: RefineResponse = await response.json();

      // Update the query with the refined version
      setQuery(refineResult.refined_query);

      // Show success toast with reasoning
      toast({
        title: "✨ Query refined!",
        description:
          refineResult.reasoning ||
          "Your query has been enhanced for better results",
        duration: 3000,
      });

      // Auto-trigger search with refined query
      setTimeout(() => {
        const params = new URLSearchParams(searchParams);
        params.set("q", refineResult.refined_query);
        params.set("type", searchType);
        router.push(`/?${params.toString()}`);
      }, 500); // Small delay to show the refined query in the input
    } catch (error) {
      console.error("Refine error:", error);
      toast({
        title: "Refinement failed",
        description:
          "There was an error enhancing your query. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsRefining(false);
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto space-y-4">
      {/* Search Type Selector */}
      <div className="flex gap-2 justify-center">
        {Object.entries(searchTypeConfig).map(([type, config]) => {
          const Icon = config.icon;
          const isActive = searchType === type;
          return (
            <Button
              key={type}
              variant={isActive ? "default" : "outline"}
              size="sm"
              onClick={() => setSearchType(type as SearchType)}
              className="flex items-center gap-2 px-4 py-2"
            >
              <Icon className="h-4 w-4" />
              {config.label}
            </Button>
          );
        })}
      </div>

      <form onSubmit={handleSearch}>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Input
              type="text"
              placeholder={currentConfig.placeholder}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-4 pr-10 py-6 text-base rounded-lg border border-gray-300 dark:border-gray-700 focus:ring-2 focus:ring-primary"
            />
          </div>
          <Button
            type="submit"
            disabled={isSearching || isRefining}
            className="px-6 py-6"
          >
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
      </form>

      <p className="text-xs text-gray-500 dark:text-gray-400">
        <strong>🔍 {currentConfig.label}:</strong> {currentConfig.description}
        <br />
        {currentConfig.examples}
      </p>
    </div>
  );
}
