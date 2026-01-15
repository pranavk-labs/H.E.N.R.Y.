"""Tests for todo/task management system."""

import pytest
from datetime import datetime, timezone

from backend.services.knowledge_service import KnowledgeService, Todo, Category
from backend.services.screen_manager import ScreenManager
from tools.base import ToolContext
from tools.todo_tool import TodoTool


@pytest.fixture
def knowledge_service():
    """Create a fresh knowledge service for testing."""
    service = KnowledgeService()
    yield service
    # Cleanup is automatic with in-memory graph


@pytest.fixture
def screen_manager():
    """Create a screen manager for testing."""
    # Reset singleton for clean state
    ScreenManager._instance = None
    return ScreenManager.get_instance()


@pytest.fixture
def tool_context(knowledge_service, screen_manager):
    """Create tool context."""
    return ToolContext(
        knowledge_service=knowledge_service,
        screen_manager=screen_manager,
    )


@pytest.fixture
def todo_tool(tool_context):
    """Create todo tool instance."""
    return TodoTool(tool_context)


class TestKnowledgeServiceTodos:
    """Test KnowledgeService todo operations."""

    def test_create_todo(self, knowledge_service):
        """Test creating a todo."""
        todo = knowledge_service.create_todo(
            title="Test Task",
            description="Test description",
            priority="high",
            difficulty=4,
        )

        assert todo.id is not None
        assert todo.title == "Test Task"
        assert todo.description == "Test description"
        assert todo.status == "todo"
        assert todo.priority == "high"
        assert todo.difficulty == 4
        assert todo.created_at is not None

    def test_get_todo(self, knowledge_service):
        """Test retrieving a todo."""
        todo = knowledge_service.create_todo(title="Test Task")
        retrieved = knowledge_service.get_todo(todo.id)

        assert retrieved is not None
        assert retrieved.id == todo.id
        assert retrieved.title == todo.title

    def test_update_todo(self, knowledge_service):
        """Test updating a todo."""
        todo = knowledge_service.create_todo(title="Original Title")
        updated = knowledge_service.update_todo(
            todo.id,
            title="Updated Title",
            status="in_progress",
            priority="critical",
        )

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.status == "in_progress"
        assert updated.priority == "critical"
        assert updated.updated_at is not None

    def test_delete_todo(self, knowledge_service):
        """Test deleting a todo."""
        todo = knowledge_service.create_todo(title="To Delete")
        result = knowledge_service.delete_todo(todo.id)

        assert result is True
        assert knowledge_service.get_todo(todo.id) is None

    def test_list_todos(self, knowledge_service):
        """Test listing todos."""
        todo1 = knowledge_service.create_todo(title="Task 1", priority="high")
        todo2 = knowledge_service.create_todo(title="Task 2", priority="low")
        todo3 = knowledge_service.create_todo(title="Task 3", status="completed")

        # List all
        all_todos = knowledge_service.list_todos()
        assert len(all_todos) >= 3

        # Filter by priority
        high_priority = knowledge_service.list_todos(priority="high")
        assert len(high_priority) >= 1
        assert any(t.id == todo1.id for t in high_priority)

        # Filter by status
        completed = knowledge_service.list_todos(status="completed")
        assert len(completed) >= 1
        assert any(t.id == todo3.id for t in completed)

    def test_create_category(self, knowledge_service):
        """Test creating a category."""
        category = knowledge_service.create_category(
            name="Work",
            color="#ff0000",
            icon="💼",
        )

        assert category.id is not None
        assert category.name == "Work"
        assert category.color == "#ff0000"
        assert category.icon == "💼"

    def test_list_categories(self, knowledge_service):
        """Test listing categories."""
        cat1 = knowledge_service.create_category(name="Personal")
        cat2 = knowledge_service.create_category(name="Work")

        categories = knowledge_service.list_categories()
        assert len(categories) >= 2
        assert any(c.id == cat1.id for c in categories)
        assert any(c.id == cat2.id for c in categories)

    def test_todo_with_category(self, knowledge_service):
        """Test creating a todo with a category."""
        category = knowledge_service.create_category(name="Work")
        todo = knowledge_service.create_todo(
            title="Work Task",
            category_id=category.id,
        )

        assert todo.category_id == category.id

        # List todos by category
        work_todos = knowledge_service.get_todos_by_category(category.id)
        assert len(work_todos) >= 1
        assert any(t.id == todo.id for t in work_todos)

    def test_subtasks(self, knowledge_service):
        """Test creating and retrieving subtasks."""
        parent = knowledge_service.create_todo(title="Parent Task")
        subtask1 = knowledge_service.create_todo(
            title="Subtask 1",
            parent_todo_id=parent.id,
        )
        subtask2 = knowledge_service.create_todo(
            title="Subtask 2",
            parent_todo_id=parent.id,
        )

        subtasks = knowledge_service.get_subtasks(parent.id)
        assert len(subtasks) == 2
        assert any(t.id == subtask1.id for t in subtasks)
        assert any(t.id == subtask2.id for t in subtasks)

    def test_link_todo_to_idea(self, knowledge_service):
        """Test linking a todo to an idea."""
        idea = knowledge_service.create_idea(text="Great idea", tags=["test"])
        todo = knowledge_service.create_todo(title="Implement idea")

        result = knowledge_service.link_todo_to_idea(todo.id, idea.id)
        assert result is True

    def test_add_todo_dependency(self, knowledge_service):
        """Test adding a dependency between todos."""
        todo1 = knowledge_service.create_todo(title="Blocker Task")
        todo2 = knowledge_service.create_todo(title="Dependent Task")

        result = knowledge_service.add_todo_dependency(todo2.id, todo1.id)
        assert result is True

    def test_recurring_todos(self, knowledge_service):
        """Test recurring todo generation."""
        # Create a daily recurring todo template
        template = knowledge_service.create_todo(
            title="Daily Standup",
            recurrence_pattern="daily",
        )

        # Manually set updated_at to yesterday to trigger generation
        from datetime import timedelta
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        knowledge_service.update_todo(
            template.id,
            updated_at=yesterday.isoformat(),
        )

        # Check and create recurring instances
        created = knowledge_service.check_and_create_recurring_todos()

        # Should create one instance
        assert len(created) >= 1
        assert created[0].title == "Daily Standup"
        assert created[0].recurrence_pattern == "none"  # Instances don't recur


class TestTodoTool:
    """Test TodoTool operations."""

    def test_create_todo_action(self, todo_tool):
        """Test creating a todo via tool."""
        result = todo_tool.execute(
            "create",
            title="Tool Test Task",
            description="Created via tool",
            priority="medium",
            difficulty=3,
        )

        assert result["action"] == "created"
        assert "todo" in result
        assert result["todo"]["title"] == "Tool Test Task"

    def test_list_todos_action(self, todo_tool):
        """Test listing todos via tool."""
        # Create some todos
        todo_tool.execute("create", title="Task 1")
        todo_tool.execute("create", title="Task 2", priority="high")

        result = todo_tool.execute("list")

        assert "todos" in result
        assert "count" in result
        assert result["count"] >= 2

    def test_update_todo_action(self, todo_tool):
        """Test updating a todo via tool."""
        create_result = todo_tool.execute("create", title="Original")
        todo_id = create_result["todo"]["id"]

        update_result = todo_tool.execute(
            "update",
            todo_id=todo_id,
            title="Updated",
            status="in_progress",
        )

        assert update_result["action"] == "updated"
        assert update_result["todo"]["title"] == "Updated"
        assert update_result["todo"]["status"] == "in_progress"

    def test_complete_todo_action(self, todo_tool):
        """Test completing a todo via tool."""
        create_result = todo_tool.execute("create", title="To Complete")
        todo_id = create_result["todo"]["id"]

        complete_result = todo_tool.execute("complete", todo_id=todo_id)

        assert complete_result["action"] == "completed"
        assert complete_result["todo"]["status"] == "completed"

    def test_delete_todo_action(self, todo_tool):
        """Test deleting a todo via tool."""
        create_result = todo_tool.execute("create", title="To Delete")
        todo_id = create_result["todo"]["id"]

        delete_result = todo_tool.execute("delete", todo_id=todo_id)

        assert delete_result["deleted"] is True
        assert delete_result["todo_id"] == todo_id

    def test_create_category_action(self, todo_tool):
        """Test creating a category via tool."""
        result = todo_tool.execute(
            "create_category",
            name="Test Category",
            color="#00ff00",
            icon="🎯",
        )

        assert result["action"] == "created"
        assert result["category"]["name"] == "Test Category"
        assert result["category"]["color"] == "#00ff00"

    def test_list_categories_action(self, todo_tool):
        """Test listing categories via tool."""
        todo_tool.execute("create_category", name="Cat 1")
        todo_tool.execute("create_category", name="Cat 2")

        result = todo_tool.execute("list_categories")

        assert "categories" in result
        assert result["count"] >= 2

    def test_add_subtask_action(self, todo_tool):
        """Test adding a subtask via tool."""
        parent_result = todo_tool.execute("create", title="Parent")
        parent_id = parent_result["todo"]["id"]

        subtask_result = todo_tool.execute(
            "add_subtask",
            parent_todo_id=parent_id,
            title="Subtask",
        )

        assert subtask_result["action"] == "created"
        assert subtask_result["subtask"]["title"] == "Subtask"

        # Get subtasks
        subtasks_result = todo_tool.execute(
            "get_subtasks",
            parent_todo_id=parent_id,
        )

        assert subtasks_result["count"] >= 1

    def test_link_to_idea_action(self, todo_tool, knowledge_service):
        """Test linking a todo to an idea via tool."""
        # Create an idea
        idea = knowledge_service.create_idea(text="Test idea")

        # Create a todo
        todo_result = todo_tool.execute("create", title="Implement")
        todo_id = todo_result["todo"]["id"]

        # Link them
        link_result = todo_tool.execute(
            "link_to_idea",
            todo_id=todo_id,
            idea_id=idea.id,
        )

        assert link_result["linked"] is True

    def test_add_dependency_action(self, todo_tool):
        """Test adding a dependency via tool."""
        todo1_result = todo_tool.execute("create", title="Blocker")
        todo1_id = todo1_result["todo"]["id"]

        todo2_result = todo_tool.execute("create", title="Dependent")
        todo2_id = todo2_result["todo"]["id"]

        dep_result = todo_tool.execute(
            "add_dependency",
            todo_id=todo2_id,
            depends_on_id=todo1_id,
        )

        assert dep_result["linked"] is True

    def test_screen_manager_integration(self, todo_tool, screen_manager):
        """Test that todo tool updates screen manager state."""
        result = todo_tool.execute("create", title="Screen Test")
        todo_id = result["todo"]["id"]

        # Check that active todo was set
        active_todo_id = screen_manager.get_active_todo_id()
        assert active_todo_id == todo_id

        # Get todo state
        todo_state = screen_manager.get_todo_state()
        assert todo_state["active_todo_id"] == todo_id
        assert todo_state["active_todo_title"] == "Screen Test"


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_todo_lifecycle(self, todo_tool, knowledge_service):
        """Test complete lifecycle: create, update, complete, delete."""
        # Create category
        cat_result = todo_tool.execute("create_category", name="Lifecycle Test")
        category_id = cat_result["category"]["id"]

        # Create todo
        create_result = todo_tool.execute(
            "create",
            title="Lifecycle Todo",
            description="Full lifecycle test",
            category_id=category_id,
            priority="high",
            difficulty=4,
        )
        todo_id = create_result["todo"]["id"]

        # Update todo
        update_result = todo_tool.execute(
            "update",
            todo_id=todo_id,
            status="in_progress",
        )
        assert update_result["todo"]["status"] == "in_progress"

        # Complete todo
        complete_result = todo_tool.execute("complete", todo_id=todo_id)
        assert complete_result["todo"]["status"] == "completed"

        # Delete todo
        delete_result = todo_tool.execute("delete", todo_id=todo_id)
        assert delete_result["deleted"] is True

        # Verify deletion
        assert knowledge_service.get_todo(todo_id) is None

    def test_complex_task_structure(self, todo_tool, knowledge_service):
        """Test complex structure with categories, subtasks, and dependencies."""
        # Create category
        cat_result = todo_tool.execute("create_category", name="Project")
        category_id = cat_result["category"]["id"]

        # Create main task
        main_result = todo_tool.execute(
            "create",
            title="Main Project Task",
            category_id=category_id,
        )
        main_id = main_result["todo"]["id"]

        # Create subtasks
        subtask1_result = todo_tool.execute(
            "add_subtask",
            parent_todo_id=main_id,
            title="Subtask 1",
        )
        subtask1_id = subtask1_result["subtask"]["id"]

        subtask2_result = todo_tool.execute(
            "add_subtask",
            parent_todo_id=main_id,
            title="Subtask 2",
        )
        subtask2_id = subtask2_result["subtask"]["id"]

        # Add dependency (subtask2 depends on subtask1)
        dep_result = todo_tool.execute(
            "add_dependency",
            todo_id=subtask2_id,
            depends_on_id=subtask1_id,
        )
        assert dep_result["linked"] is True

        # Verify structure
        subtasks = knowledge_service.get_subtasks(main_id)
        assert len(subtasks) == 2

        # List by category
        category_todos = knowledge_service.get_todos_by_category(category_id)
        assert len(category_todos) >= 3  # Main + 2 subtasks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

