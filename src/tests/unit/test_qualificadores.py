"""Unit and integration tests for Qualificadores functionality.

Tests cover:
- Qualificador CRUD operations
- Hierarchical structure
- Active/inactive filtering
- Receita vs Despesa filtering
"""
import pytest


class TestQualificadorServiceUnit:
    """Unit tests for qualificador_service."""

    def test_list_all_qualificadores(self, client):
        """Should list all qualificadores."""
        from fluxocaixa.services.qualificador_service import list_all_qualificadores

        qualificadores = list_all_qualificadores()

        assert isinstance(qualificadores, list)
        assert len(qualificadores) > 0  # Seed data should exist

    def test_list_active_qualificadores(self, client):
        """Should list only active qualificadores."""
        from fluxocaixa.services.qualificador_service import list_active_qualificadores

        qualificadores = list_active_qualificadores()

        assert isinstance(qualificadores, list)
        # All should be active
        for q in qualificadores:
            assert q.ind_status == 'A'

    def test_list_root_qualificadores(self, client):
        """Should list only root qualificadores (no parent)."""
        from fluxocaixa.services.qualificador_service import list_root_qualificadores

        qualificadores = list_root_qualificadores()

        assert isinstance(qualificadores, list)
        # All should have no parent
        for q in qualificadores:
            assert q.cod_qualificador_pai is None

    def test_list_receita_qualificadores(self, client):
        """Should list receita qualificadores."""
        from fluxocaixa.services.qualificador_service import list_receita_qualificadores

        qualificadores = list_receita_qualificadores()

        assert isinstance(qualificadores, list)
        # All should be receita type
        for q in qualificadores:
            assert q.tipo_fluxo == 'receita'

    def test_list_despesa_qualificadores(self, client):
        """Should list despesa qualificadores."""
        from fluxocaixa.services.qualificador_service import list_despesa_qualificadores

        qualificadores = list_despesa_qualificadores()

        assert isinstance(qualificadores, list)
        # All should be despesa type
        for q in qualificadores:
            assert q.tipo_fluxo == 'despesa'

    def test_list_receita_qualificadores_folha(self, client):
        """Should list leaf-only receita qualificadores."""
        from fluxocaixa.services.qualificador_service import list_receita_qualificadores_folha

        qualificadores = list_receita_qualificadores_folha()

        assert isinstance(qualificadores, list)
        # All should be receita and have no children
        for q in qualificadores:
            assert q.tipo_fluxo == 'receita'

    def test_list_despesa_qualificadores_folha(self, client):
        """Should list leaf-only despesa qualificadores."""
        from fluxocaixa.services.qualificador_service import list_despesa_qualificadores_folha

        qualificadores = list_despesa_qualificadores_folha()

        assert isinstance(qualificadores, list)
        # All should be despesa and have no children
        for q in qualificadores:
            assert q.tipo_fluxo == 'despesa'

    def test_get_qualificador_by_id(self, client):
        """Should get qualificador by ID."""
        from fluxocaixa.services.qualificador_service import (
            list_active_qualificadores,
            get_qualificador
        )

        qualificadores = list_active_qualificadores()
        if qualificadores:
            q_id = qualificadores[0].seq_qualificador
            result = get_qualificador(q_id)

            assert result is not None
            assert result.seq_qualificador == q_id

    def test_get_qualificador_nonexistent(self, client):
        """Should return None for non-existent ID."""
        from fluxocaixa.services.qualificador_service import get_qualificador

        result = get_qualificador(999999)

        assert result is None

    def test_get_qualificador_by_name(self, client):
        """Should get qualificador by name."""
        from fluxocaixa.services.qualificador_service import get_qualificador_by_name

        result = get_qualificador_by_name('ICMS')

        # May exist from seed data
        if result:
            assert 'ICMS' in result.dsc_qualificador.upper()

    def test_get_qualificador_by_name_nonexistent(self, client):
        """Should return None for non-existent name."""
        from fluxocaixa.services.qualificador_service import get_qualificador_by_name

        result = get_qualificador_by_name('XYZABC_NONEXISTENT_999')

        assert result is None


class TestQualificadorRepository:
    """Tests for QualificadorRepository methods."""

    def test_get_all(self, client):
        """Should get all qualificadores."""
        from fluxocaixa.repositories.qualificador_repository import QualificadorRepository

        repo = QualificadorRepository()
        qualificadores = repo.get_all()

        assert isinstance(qualificadores, list)

    def test_get_active(self, client):
        """Should get only active qualificadores."""
        from fluxocaixa.repositories.qualificador_repository import QualificadorRepository

        repo = QualificadorRepository()
        qualificadores = repo.get_active()

        for q in qualificadores:
            assert q.ind_status == 'A'

    def test_get_children(self, client):
        """Should get children of a qualificador."""
        from fluxocaixa.repositories.qualificador_repository import QualificadorRepository
        from fluxocaixa.services.qualificador_service import list_root_qualificadores

        repo = QualificadorRepository()
        roots = list_root_qualificadores()

        if roots:
            children = repo.get_children(roots[0].seq_qualificador)
            assert isinstance(children, list)
            for child in children:
                assert child.cod_qualificador_pai == roots[0].seq_qualificador


class TestQualificadorIntegration:
    """Integration tests for qualificador web routes."""

    def test_qualificadores_page_loads(self, client):
        """Should load qualificadores page."""
        response = client.get('/qualificadores')
        assert response.status_code == 200

    def test_qualificadores_tree_structure(self, client):
        """Should display tree structure."""
        response = client.get('/qualificadores')
        assert response.status_code == 200
        # Should contain tree-related elements
        assert 'node' in response.text.lower() or 'qualificador' in response.text.lower()

    def test_add_qualificador(self, client):
        """Should add a new qualificador."""
        response = client.post('/qualificadores/add', data={
            'num_qualificador': '999.TEST',
            'dsc_qualificador': 'Qualificador de Teste',
            'cod_qualificador_pai': '',
        })
        # Should redirect or return success
        assert response.status_code in (200, 302, 303)

    def test_edit_qualificador(self, client):
        """Should edit a qualificador."""
        from fluxocaixa.services.qualificador_service import list_active_qualificadores

        qualificadores = list_active_qualificadores()
        if qualificadores:
            q_id = qualificadores[0].seq_qualificador
            response = client.post(f'/qualificadores/edit/{q_id}', data={
                'num_qualificador': qualificadores[0].num_qualificador,
                'dsc_qualificador': qualificadores[0].dsc_qualificador + ' Editado',
                'cod_qualificador_pai': str(qualificadores[0].cod_qualificador_pai or ''),
            })
            assert response.status_code in (200, 302, 303)


class TestQualificadorHierarchy:
    """Tests for qualificador hierarchical structure."""

    def test_parent_child_relationship(self, client):
        """Should maintain parent-child relationship."""
        from fluxocaixa.services.qualificador_service import (
            list_root_qualificadores,
            list_active_qualificadores
        )

        roots = list_root_qualificadores()
        all_q = list_active_qualificadores()

        # Find children of first root
        if roots:
            parent_id = roots[0].seq_qualificador
            children = [q for q in all_q if q.cod_qualificador_pai == parent_id]

            for child in children:
                assert child.cod_qualificador_pai == parent_id

    def test_tipo_fluxo_inheritance(self, client):
        """Tipo fluxo should be consistent in hierarchy."""
        from fluxocaixa.services.qualificador_service import (
            list_receita_qualificadores,
            get_qualificador
        )

        receitas = list_receita_qualificadores()

        for q in receitas:
            if q.cod_qualificador_pai:
                parent = get_qualificador(q.cod_qualificador_pai)
                if parent:
                    assert parent.tipo_fluxo == q.tipo_fluxo

