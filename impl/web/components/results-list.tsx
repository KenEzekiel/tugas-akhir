"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { searchContracts } from "@/lib/actions";
import { ContractDetails } from "@/components/contract-details";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ContractResult, SearchType } from "@/lib/types";
import {
  Copy,
  ExternalLink,
  FileCode,
  Tag,
  Shield,
  Zap,
  Layers,
  Target,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

// Helper function to get relevance level and color
function getRelevanceInfo(score?: number) {
  if (score === undefined || score === null) {
    return { level: "Unknown", color: "bg-gray-500", textColor: "text-white" };
  }

  if (score > 0.6) {
    return { level: "High", color: "bg-green-500", textColor: "text-white" };
  } else if (score >= 0.3) {
    return { level: "Medium", color: "bg-yellow-500", textColor: "text-black" };
  } else {
    return { level: "Low", color: "bg-red-500", textColor: "text-white" };
  }
}

// Helper function to render attribute badges with icons
function AttributeBadges({
  items,
  icon: Icon,
  variant = "secondary" as const,
  maxItems = 3,
}: {
  items?: string[];
  icon: any;
  variant?: "default" | "secondary" | "destructive" | "outline";
  maxItems?: number;
}) {
  if (!items || items.length === 0) return null;

  const displayItems = items.slice(0, maxItems);
  const remainingCount = items.length - maxItems;

  return (
    <div className="flex flex-wrap gap-1">
      {displayItems.map((item, i) => (
        <Badge
          key={`${item}-${i}`}
          variant={variant}
          className="flex items-center gap-1 text-xs"
        >
          <Icon className="h-3 w-3" />
          {item}
        </Badge>
      ))}
      {remainingCount > 0 && (
        <Badge variant="outline" className="text-xs">
          +{remainingCount} more
        </Badge>
      )}
    </div>
  );
}

export function ResultsList() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q");
  const threshold = parseFloat(searchParams.get("threshold") || "0.7");
  const searchType = (searchParams.get("type") as SearchType) || "vector";
  const { toast } = useToast();

  const [results, setResults] = useState<ContractResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedContract, setSelectedContract] = useState<string | null>(null);
  const [contractDetails, setContractDetails] = useState<ContractResult | null>(
    null
  );
  const [loadingDetails, setLoadingDetails] = useState(false);

  useEffect(() => {
    async function fetchResults() {
      if (!query) return;

      setLoading(true);
      try {
        const data = await searchContracts(query, 10, threshold, searchType);
        console.log(data, `${searchType} search data`);
        setResults(data);
      } catch (error) {
        console.error("Error fetching results:", error);
        toast({
          title: "Error",
          description: "Failed to fetch search results. Please try again.",
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    }

    fetchResults();
  }, [query, threshold, searchType, toast]);

  const handleViewDetails = async (contractId: string) => {
    setSelectedContract(contractId);
    setLoadingDetails(true);

    try {
      const contract = results.find((r) => r.id === contractId);
      if (!contract) {
        throw new Error("Contract not found");
      }

      setContractDetails(contract);
    } catch (error) {
      console.error("Error fetching contract details:", error);
      toast({
        title: "Error",
        description: "Failed to load contract details. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoadingDetails(false);
    }
  };

  if (!query) {
    return (
      <div className="text-center py-12">
        <FileCode className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
          No search query
        </h3>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          Enter a search term to find smart contracts
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold mb-4">
          🔍 Vector searching for: "{query}"
        </h2>
        {[1, 2, 3].map((i) => (
          <Card key={`skeleton-${i}`} className="overflow-hidden">
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
    );
  }

  if (selectedContract && contractDetails) {
    return (
      <ContractDetails
        contract={contractDetails}
        onBack={() => {
          setSelectedContract(null);
          setContractDetails(null);
        }}
      />
    );
  }

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">
        🔍 {results.length} results for: "{query}"
      </h2>

      {results.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
          <FileCode className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
            No similar contracts found
          </h3>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Try adjusting your search terms
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {results
            .slice() // copy to avoid mutating state
            .sort((a, b) => {
              // Sort descending by similarity_score, undefined/null last
              if (a.similarity_score == null && b.similarity_score == null)
                return 0;
              if (a.similarity_score == null) return 1;
              if (b.similarity_score == null) return -1;
              return b.similarity_score - a.similarity_score;
            })
            .map((contract, index) => {
              const relevanceInfo = getRelevanceInfo(contract.similarity_score);

              return (
                <Card
                  key={`${contract.id}-${contract.name}`}
                  className="overflow-hidden hover:shadow-md transition-shadow"
                >
                  <CardHeader className="pb-2">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <CardTitle className="text-lg flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded-full">
                            #{index + 1}
                          </span>
                          {contract.name || "Unnamed Contract"}
                        </CardTitle>
                        <CardDescription>
                          {contract.description || "No description available"}
                        </CardDescription>
                      </div>
                      <div className="flex flex-col gap-2 items-end">
                        {/* Similarity Score Badge */}
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-1 rounded-full text-xs font-medium ${relevanceInfo.color} ${relevanceInfo.textColor}`}
                          >
                            {relevanceInfo.level} Relevance
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {contract.similarity_score !== undefined
                              ? `${(contract.similarity_score * 100).toFixed(
                                  1
                                )}%`
                              : "N/A"}
                          </span>
                        </div>

                        {/* Status badges */}
                        <div className="flex gap-2">
                          {contract.verified && (
                            <Badge variant="default">Verified</Badge>
                          )}
                          {contract.experimental && (
                            <Badge variant="outline">Experimental</Badge>
                          )}
                          {contract.solc_version && (
                            <Badge variant="outline">
                              Solidity {contract.solc_version}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {/* Tags and Domain */}
                    <div className="flex flex-wrap gap-2">
                      {contract.tags?.map((tag, i) => (
                        <Badge
                          key={`${tag}-${i}`}
                          variant="secondary"
                          className="flex items-center gap-1"
                        >
                          <Tag className="h-3 w-3" />
                          {tag}
                        </Badge>
                      ))}
                      {contract.domain && (
                        <Badge
                          variant="secondary"
                          className="flex items-center gap-1"
                        >
                          <Target className="h-3 w-3" />
                          {contract.domain}
                        </Badge>
                      )}
                    </div>

                    {/* Standards */}
                    {contract.standards && contract.standards.length > 0 && (
                      <div className="space-y-1">
                        <p className="text-xs font-medium text-gray-600 dark:text-gray-400 flex items-center gap-1">
                          <Layers className="h-3 w-3" />
                          Standards:
                        </p>
                        <AttributeBadges
                          items={contract.standards}
                          icon={Layers}
                          variant="default"
                        />
                      </div>
                    )}

                    {/* Patterns */}
                    {contract.patterns && contract.patterns.length > 0 && (
                      <div className="space-y-1">
                        <p className="text-xs font-medium text-gray-600 dark:text-gray-400 flex items-center gap-1">
                          <Zap className="h-3 w-3" />
                          Patterns:
                        </p>
                        <AttributeBadges
                          items={contract.patterns}
                          icon={Zap}
                          variant="secondary"
                        />
                      </div>
                    )}

                    {/* Functionalities */}
                    {contract.functionalities &&
                      contract.functionalities.length > 0 && (
                        <div className="space-y-1">
                          <p className="text-xs font-medium text-gray-600 dark:text-gray-400 flex items-center gap-1">
                            <Zap className="h-3 w-3" />
                            Functionalities:
                          </p>
                          <AttributeBadges
                            items={contract.functionalities}
                            icon={Zap}
                            variant="secondary"
                          />
                        </div>
                      )}

                    {/* Security Risks */}
                    {contract.security_risks &&
                      contract.security_risks.length > 0 && (
                        <div className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                          <p className="font-medium">
                            Security Considerations:{" "}
                          </p>
                          <p>{contract.security_risks}</p>
                        </div>
                      )}
                  </CardContent>
                  <CardFooter className="flex flex-wrap gap-2">
                    <Button
                      variant="default"
                      onClick={() => handleViewDetails(contract.id)}
                      disabled={
                        loadingDetails && selectedContract === contract.id
                      }
                    >
                      {loadingDetails && selectedContract === contract.id ? (
                        <span className="flex items-center gap-2">
                          <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                          Loading...
                        </span>
                      ) : (
                        <span className="flex items-center gap-2">
                          View Details
                        </span>
                      )}
                    </Button>

                    {contract.address && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          navigator.clipboard.writeText(contract.address!);
                          toast({
                            title: "Address copied",
                            description: "Contract address copied to clipboard",
                          });
                        }}
                        className="flex items-center gap-1"
                      >
                        <Copy className="h-3.5 w-3.5" />
                        Copy Address
                      </Button>
                    )}

                    {contract.externalUrl && (
                      <Button
                        variant="outline"
                        size="icon"
                        asChild
                        className="ml-auto"
                      >
                        <a
                          href={contract.externalUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="h-4 w-4" />
                          <span className="sr-only">External link</span>
                        </a>
                      </Button>
                    )}
                  </CardFooter>
                </Card>
              );
            })}
        </div>
      )}
    </div>
  );
}
