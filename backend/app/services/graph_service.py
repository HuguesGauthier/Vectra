import logging
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable, AuthError

logger = logging.getLogger(__name__)


class GraphService:
    """
    Manages connections and operations to Neo4j.
    """

    def __init__(self, uri: str, user: str, password: Optional[str]):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Optional[AsyncDriver] = None

    async def connect(self):
        """Initialize the Neo4j driver and setup constraints."""
        if not self.driver:
            try:
                auth = (self.user, self.password) if self.password else None
                self.driver = AsyncGraphDatabase.driver(self.uri, auth=auth)
                # Verify connectivity
                await self.driver.verify_connectivity()
                logger.info(f"Connected to Neo4j at {self.uri}")

                # Setup Constraints
                async with self.driver.session() as session:
                    await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE")
            except (ServiceUnavailable, AuthError) as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                self.driver = None
                raise

    async def close(self):
        """Close the Neo4j driver."""
        if self.driver:
            await self.driver.close()
            self.driver = None
            logger.info("Closed Neo4j connection")

    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return the results as a list of dictionaries.
        """
        if not self.driver:
            await self.connect()

        if not self.driver:
            raise RuntimeError("Neo4j driver not initialized.")

        try:
            records, summary, keys = await self.driver.execute_query(query, parameters_=parameters)
            return [record.data() for record in records]
        except Exception as e:
            logger.error(f"Error executing Cypher query: {e}")
            raise

    async def create_nodes_and_relationships(self, nodes: List[Dict], relationships: List[Dict], document_id: str):
        """
        Batch creation of nodes and relationships based on extracted graph data.
        Tags everything with document_id for later cleanup.
        Uses UNWIND for high performance.
        """
        if not self.driver:
            await self.connect()

        if not self.driver:
            raise RuntimeError("Neo4j driver not initialized.")

        try:
            async with self.driver.session() as session:
                # 1. Create Nodes in batch
                # To handle dynamic labels, we group nodes by label or just use the base Entity label
                # Since we want to be fast, we'll do one UNWIND for the base Entity label + properties
                for node in nodes:
                    node["_doc_id"] = document_id  # Ensure doc_id is in props

                # Group by label to allow SET n:Label
                nodes_by_label = {}
                for node in nodes:
                    lbl = node.get("label", "Entity")
                    if lbl not in nodes_by_label:
                        nodes_by_label[lbl] = []
                    nodes_by_label[lbl].append(node)

                for lbl, batch in nodes_by_label.items():
                    # Sanitize label - only alphanumeric and underscores
                    safe_lbl = "".join(c for c in lbl if c.isalnum() or c == "_")

                    # Prepare clean batch: flatten properties
                    clean_batch = []
                    for node in batch:
                        # Extract and flatten
                        props = node.pop("properties", {})
                        node.update(props)
                        node.pop("label", None)  # Don't store label as property since it's a Label
                        clean_batch.append(node)

                    cypher = f"""
                    UNWIND $batch AS row
                    MERGE (n:Entity {{id: row.id}})
                    SET n:`{safe_lbl}`, n += row
                    """
                    await session.run(cypher, batch=clean_batch)

                # 2. Create Relationships in batch
                # Group by rel_type for performance
                rels_by_type = {}
                for rel in relationships:
                    rel["_doc_id"] = document_id
                    rtype = rel.get("type", "RELATED_TO")
                    if rtype not in rels_by_type:
                        rels_by_type[rtype] = []
                    rels_by_type[rtype].append(rel)

                for rtype, batch in rels_by_type.items():
                    safe_rtype = "".join(c for c in rtype if c.isalnum() or c == "_")

                    clean_batch = []
                    for rel in batch:
                        props = rel.pop("properties", {})
                        rel.update(props)
                        rel.pop("type", None)  # Don't store type as property since it's a Type
                        clean_batch.append(rel)

                    cypher = f"""
                    UNWIND $batch AS row
                    MATCH (a:Entity {{id: row.source}})
                    MATCH (b:Entity {{id: row.target}})
                    MERGE (a)-[r:`{safe_rtype}`]->(b)
                    SET r += row
                    """
                    await session.run(cypher, batch=clean_batch)

            logger.info(f"✅ Successfully saved {len(nodes)} nodes and {len(relationships)} relationships to Neo4j.")
        except Exception as e:
            logger.error(f"❌ Neo4j batch insertion failed: {e}")
            raise

    async def delete_by_document_id(self, document_id: str):
        """
        Delete all nodes and relationships associated with a specific document_id.
        """
        if not self.driver:
            await self.connect()

        try:
            async with self.driver.session() as session:
                logger.info(f"🗑️ Deleting Neo4j data for Document {document_id}")
                # Use a single query for efficiency
                await session.run("MATCH ()-[r { _doc_id: $doc_id }]-() DELETE r", doc_id=document_id)
                await session.run("MATCH (n:Entity { _doc_id: $doc_id }) DELETE n", doc_id=document_id)
                logger.info(f"✅ Neo4j data for {document_id} cleared.")
        except Exception as e:
            logger.error(f"❌ Failed to delete Neo4j data for {document_id}: {e}")


async def get_graph_service() -> GraphService:
    """Dependency provider for GraphService."""
    from app.core.settings import settings

    service = GraphService(
        uri=settings.NEO4J_URI or "bolt://localhost:7687",
        user=settings.NEO4J_USER or "neo4j",
        password=settings.NEO4J_PASSWORD,
    )
    # We don't connect here to keep it lazy
    return service
