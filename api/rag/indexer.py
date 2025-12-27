"""
One-time indexing script for RAG.

Indexes:
1. Markdown documentation files (chunked by headers)
2. CSV case studies (each row as a document)

Run with: python -m api.rag.indexer
"""
import sys
from pathlib import Path
import pandas as pd
import chromadb

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.config import settings
from api.rag.chunking import chunk_all_markdown_files, csv_row_to_text
from api.rag.embedder import get_embedding, get_embeddings_batch


def create_chroma_client() -> chromadb.Client:
    """Create persistent ChromaDB client."""
    chroma_path = Path(settings.chromadb_path)
    chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(chroma_path))


def index_markdown_docs(
    client: chromadb.Client,
    docs_dir: Path
) -> int:
    """Index markdown documentation files.

    Args:
        client: ChromaDB client
        docs_dir: Directory containing .md files

    Returns:
        Number of chunks indexed
    """
    print(f"\n📚 Indexing markdown documentation from {docs_dir}...")

    if not docs_dir.exists():
        print(f"  ⚠️ Directory not found: {docs_dir}")
        print("  Creating empty docs directory...")
        docs_dir.mkdir(parents=True, exist_ok=True)
        return 0

    # Get or create collection
    collection = client.get_or_create_collection(
        name="documentation",
        metadata={"description": "Isabella2 documentation chunks"}
    )

    # Chunk all markdown files
    chunks = chunk_all_markdown_files(docs_dir)

    if not chunks:
        print("  ⚠️ No markdown files found in docs/")
        return 0

    # Generate embeddings
    print(f"  Generating embeddings for {len(chunks)} chunks...")
    texts = [chunk["text"] for chunk in chunks]
    embeddings = get_embeddings_batch(texts)

    # Add to collection
    ids = [f"doc_{i}" for i in range(len(chunks))]
    metadatas = [chunk["metadata"] for chunk in chunks]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(f"  ✅ Indexed {len(chunks)} documentation chunks")
    return len(chunks)


def index_csv_case_studies(
    client: chromadb.Client,
    inputs_dir: Path,
    time_horizon: int
) -> int:
    """Index CSV case studies for a specific time horizon.

    Args:
        client: ChromaDB client
        inputs_dir: Directory containing CSV files
        time_horizon: Climate scenario year (2020, 2050, 2100)

    Returns:
        Number of rows indexed
    """
    print(f"\n🏠 Indexing {time_horizon} case studies...")

    # Find CSV file for this time horizon
    csv_patterns = [
        f"{time_horizon}_merged_simulation_results.csv",
        f"simulation_results_{time_horizon}.csv",
        f"{time_horizon}.csv"
    ]

    csv_file = None
    for pattern in csv_patterns:
        potential_path = inputs_dir / pattern
        if potential_path.exists():
            csv_file = potential_path
            break

    if not csv_file:
        print(f"  ⚠️ No CSV found for {time_horizon} in {inputs_dir}")
        return 0

    # Read CSV
    df = pd.read_csv(csv_file)
    print(f"  Found {len(df)} rows in {csv_file.name}")

    # Get or create collection
    collection = client.get_or_create_collection(
        name=f"case_studies_{time_horizon}",
        metadata={
            "description": f"Building simulation results for {time_horizon}",
            "time_horizon": time_horizon
        }
    )

    # Convert rows to text and generate embeddings in batches
    batch_size = 100
    total_indexed = 0

    for i in range(0, len(df), batch_size):
        batch_df = df.iloc[i:i + batch_size]

        texts = []
        metadatas = []
        ids = []

        for idx, row in batch_df.iterrows():
            text = csv_row_to_text(row.to_dict(), time_horizon)
            texts.append(text)

            # Extract key metrics for metadata filtering
            metadata = {
                "time_horizon": time_horizon,
                "simulation_id": str(row.get("Simulation ID", idx)),
                "windows_U": float(row.get("windows_U_Factor", 0)),
                "source": csv_file.name
            }
            metadatas.append(metadata)
            ids.append(f"case_{time_horizon}_{idx}")

        # Generate embeddings
        embeddings = get_embeddings_batch(texts)

        # Add to collection
        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )

        total_indexed += len(texts)
        print(f"  Indexed {total_indexed}/{len(df)} rows...", end="\r")

    print(f"\n  ✅ Indexed {total_indexed} case studies for {time_horizon}")
    return total_indexed


def run_indexing():
    """Run full indexing pipeline."""
    print("=" * 60)
    print("Isabella2 RAG Indexer")
    print("=" * 60)

    # Create ChromaDB client
    client = create_chroma_client()
    print(f"ChromaDB path: {settings.chromadb_path}")

    # Paths
    docs_dir = PROJECT_ROOT / "docs"
    inputs_dir = PROJECT_ROOT / "inputs"

    # Index documentation
    doc_count = index_markdown_docs(client, docs_dir)

    # Index case studies for each time horizon
    case_counts = {}
    for year in [2020, 2050, 2100]:
        count = index_csv_case_studies(client, inputs_dir, year)
        case_counts[year] = count

    # Summary
    print("\n" + "=" * 60)
    print("📊 Indexing Complete!")
    print("=" * 60)
    print(f"Documentation chunks: {doc_count}")
    for year, count in case_counts.items():
        print(f"Case studies {year}: {count}")
    print(f"Total documents: {doc_count + sum(case_counts.values())}")


if __name__ == "__main__":
    run_indexing()
