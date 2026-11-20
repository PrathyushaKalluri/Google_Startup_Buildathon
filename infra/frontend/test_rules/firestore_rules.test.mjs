import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { after, before, beforeEach, describe, it } from 'node:test';
import {
  assertFails,
  assertSucceeds,
  initializeTestEnvironment,
} from '@firebase/rules-unit-testing';
import {
  collection,
  deleteDoc,
  doc,
  getDoc,
  getDocs,
  query,
  setDoc,
  updateDoc,
  where,
} from 'firebase/firestore';

const __dirname = dirname(fileURLToPath(import.meta.url));
const RULES_PATH = resolve(__dirname, '../firestore.rules');
const PROJECT_ID = 'keepwell-rules-test';

const CENTRE_FW = 'c_fw_uuid';
const CENTRE_AV = 'c_av_uuid';
const TECH_FW_1 = 'tech_fw_1';
const TECH_FW_2 = 'tech_fw_2';
const TECH_AV_1 = 'tech_av_1';
const PARTS_CENTRE_1 = 'pc_1';
const PARTS_CENTRE_2 = 'pc_2';
const HOUSEHOLD_1 = 'hh_1';
const HOUSEHOLD_2 = 'hh_2';

let testEnv;

before(async () => {
  const emulatorHost = process.env.FIRESTORE_EMULATOR_HOST || '127.0.0.1:8080';
  const [host, portStr] = emulatorHost.split(':');
  testEnv = await initializeTestEnvironment({
    projectId: PROJECT_ID,
    firestore: {
      host,
      port: Number(portStr),
      rules: readFileSync(RULES_PATH, 'utf8'),
    },
  });
});

after(async () => {
  await testEnv?.cleanup();
});

beforeEach(async () => {
  await testEnv.clearFirestore();
  await testEnv.withSecurityRulesDisabled(async (ctx) => {
    const db = ctx.firestore();

    // Seed centre c_fw
    await setDoc(doc(db, `centres/${CENTRE_FW}`), { name: 'Frost and Wave' });
    await setDoc(doc(db, `centres/${CENTRE_FW}/tickets/t1`), {
      id: 't1',
      centre_id: CENTRE_FW,
      urgency_class: 'urgent',
    });
    await setDoc(doc(db, `centres/${CENTRE_FW}/feed/e1`), {
      id: 'e1',
      type: 'conversation_started',
    });
    await setDoc(doc(db, `centres/${CENTRE_FW}/conversations/conv1`), {
      channel: 'voice',
      state: 'active',
    });
    await setDoc(doc(db, `centres/${CENTRE_FW}/conversations/conv1/turns/turn1`), {
      speaker: 'household',
      text: 'Washer E21 error',
    });
    await setDoc(doc(db, `centres/${CENTRE_FW}/technicians/${TECH_FW_1}`), {
      name: 'Ravi Kumar',
      status: 'available',
    });
    await setDoc(doc(db, `centres/${CENTRE_FW}/technicians/${TECH_FW_2}`), {
      name: 'Suresh Reddy',
      status: 'on_job',
    });
    await setDoc(doc(db, `centres/${CENTRE_FW}/visits/v1`), {
      ticket_id: 't1',
      technician_id: TECH_FW_1,
      status: 'scheduled',
    });
    await setDoc(doc(db, `centres/${CENTRE_FW}/visits/v2`), {
      ticket_id: 't2',
      technician_id: TECH_FW_2,
      status: 'scheduled',
    });
    await setDoc(doc(db, `centres/${CENTRE_FW}/parts_requests/pr1`), {
      visit_id: 'v1',
      part_no: 'WC-PUMP-01',
      parts_centre_id: PARTS_CENTRE_1,
      status: 'requested',
    });
    await setDoc(doc(db, `centres/${CENTRE_FW}/parts_requests/pr2`), {
      visit_id: 'v2',
      part_no: 'WC-BELT-02',
      parts_centre_id: PARTS_CENTRE_2,
      status: 'requested',
    });

    // Seed centre c_av
    await setDoc(doc(db, `centres/${CENTRE_AV}/tickets/t_av`), {
      id: 't_av',
      centre_id: CENTRE_AV,
      urgency_class: 'standard',
    });
    await setDoc(doc(db, `centres/${CENTRE_AV}/technicians/${TECH_AV_1}`), {
      name: 'Anil Sharma',
      status: 'available',
    });
    await setDoc(doc(db, `centres/${CENTRE_AV}/visits/v_av`), {
      ticket_id: 't_av',
      technician_id: TECH_AV_1,
      status: 'scheduled',
    });

    // Seed households
    await setDoc(doc(db, `households/${HOUSEHOLD_1}/whatsapp_thread/m1`), {
      direction: 'in',
      type: 'text',
      text: 'Hello',
    });
    await setDoc(doc(db, `households/${HOUSEHOLD_2}/whatsapp_thread/m2`), {
      direction: 'in',
      type: 'text',
      text: 'Other household message',
    });

    // Seed meta/demo
    await setDoc(doc(db, 'meta/demo'), {
      active_case_id: 'C03',
    });
  });
});

describe('Keepwell Firestore Security Rules (Contract Section 6)', () => {
  it('denies all unauthenticated reads', async () => {
    const db = testEnv.unauthenticatedContext().firestore();
    await assertFails(getDoc(doc(db, `centres/${CENTRE_FW}/tickets/t1`)));
    await assertFails(getDoc(doc(db, `households/${HOUSEHOLD_1}/whatsapp_thread/m1`)));
    await assertFails(getDoc(doc(db, 'meta/demo')));
  });

  it('enforces cross-centre isolation for centre_admin', async () => {
    const fwAdmin = testEnv
      .authenticatedContext('admin_fw', {
        role: 'centre_admin',
        centre_id: CENTRE_FW,
      })
      .firestore();

    // Own centre reads succeed
    await assertSucceeds(getDoc(doc(fwAdmin, `centres/${CENTRE_FW}/tickets/t1`)));
    await assertSucceeds(getDoc(doc(fwAdmin, `centres/${CENTRE_FW}/feed/e1`)));
    await assertSucceeds(getDoc(doc(fwAdmin, `centres/${CENTRE_FW}/conversations/conv1`)));
    await assertSucceeds(
      getDoc(doc(fwAdmin, `centres/${CENTRE_FW}/conversations/conv1/turns/turn1`)),
    );
    await assertSucceeds(
      getDoc(doc(fwAdmin, `centres/${CENTRE_FW}/technicians/${TECH_FW_1}`)),
    );
    await assertSucceeds(getDoc(doc(fwAdmin, `centres/${CENTRE_FW}/visits/v1`)));
    await assertSucceeds(getDoc(doc(fwAdmin, 'meta/demo')));

    // Another centre reads fail
    await assertFails(getDoc(doc(fwAdmin, `centres/${CENTRE_AV}/tickets/t_av`)));
    await assertFails(
      getDoc(doc(fwAdmin, `centres/${CENTRE_AV}/technicians/${TECH_AV_1}`)),
    );
    await assertFails(getDoc(doc(fwAdmin, `centres/${CENTRE_AV}/visits/v_av`)));

    // Household thread read fails for centre_admin
    await assertFails(
      getDoc(doc(fwAdmin, `households/${HOUSEHOLD_1}/whatsapp_thread/m1`)),
    );
  });

  it('allows platform role to read across centres and meta/demo, but not households', async () => {
    const platformDb = testEnv
      .authenticatedContext('platform_user', { role: 'platform' })
      .firestore();

    await assertSucceeds(getDoc(doc(platformDb, `centres/${CENTRE_FW}/tickets/t1`)));
    await assertSucceeds(getDoc(doc(platformDb, `centres/${CENTRE_AV}/tickets/t_av`)));
    await assertSucceeds(getDoc(doc(platformDb, 'meta/demo')));
    await assertFails(
      getDoc(doc(platformDb, `households/${HOUSEHOLD_1}/whatsapp_thread/m1`)),
    );
  });

  it('enforces technician isolation to own technician doc and own visits only', async () => {
    const tech1Db = testEnv
      .authenticatedContext('tech_1', {
        role: 'technician',
        centre_id: CENTRE_FW,
        technician_id: TECH_FW_1,
      })
      .firestore();

    // Allowed: own technician profile, own visit doc, own filtered visits query, meta/demo
    await assertSucceeds(
      getDoc(doc(tech1Db, `centres/${CENTRE_FW}/technicians/${TECH_FW_1}`)),
    );
    await assertSucceeds(getDoc(doc(tech1Db, `centres/${CENTRE_FW}/visits/v1`)));
    await assertSucceeds(
      getDocs(
        query(
          collection(tech1Db, `centres/${CENTRE_FW}/visits`),
          where('technician_id', '==', TECH_FW_1),
        ),
      ),
    );
    await assertSucceeds(getDoc(doc(tech1Db, 'meta/demo')));

    // Denied: other technician profile, other technician visit, unfiltered visits query
    await assertFails(
      getDoc(doc(tech1Db, `centres/${CENTRE_FW}/technicians/${TECH_FW_2}`)),
    );
    await assertFails(getDoc(doc(tech1Db, `centres/${CENTRE_FW}/visits/v2`)));
    await assertFails(getDocs(collection(tech1Db, `centres/${CENTRE_FW}/visits`)));

    // Denied: centre tickets, feed, conversations, other centres
    await assertFails(getDoc(doc(tech1Db, `centres/${CENTRE_FW}/tickets/t1`)));
    await assertFails(getDoc(doc(tech1Db, `centres/${CENTRE_FW}/feed/e1`)));
    await assertFails(getDoc(doc(tech1Db, `centres/${CENTRE_FW}/conversations/conv1`)));
    await assertFails(getDoc(doc(tech1Db, `centres/${CENTRE_AV}/visits/v_av`)));
  });

  it('scopes parts_centre reads to matching parts_requests only', async () => {
    const partsDb = testEnv
      .authenticatedContext('parts_1', {
        role: 'parts_centre',
        parts_centre_id: PARTS_CENTRE_1,
      })
      .firestore();

    await assertSucceeds(
      getDoc(doc(partsDb, `centres/${CENTRE_FW}/parts_requests/pr1`)),
    );
    await assertFails(
      getDoc(doc(partsDb, `centres/${CENTRE_FW}/parts_requests/pr2`)),
    );
    await assertFails(getDoc(doc(partsDb, `centres/${CENTRE_FW}/tickets/t1`)));
  });

  it('scopes household custom token reads to own household_id only', async () => {
    const hh1Db = testEnv
      .authenticatedContext('hh_session_1', {
        household_id: HOUSEHOLD_1,
      })
      .firestore();

    await assertSucceeds(
      getDoc(doc(hh1Db, `households/${HOUSEHOLD_1}/whatsapp_thread/m1`)),
    );
    await assertSucceeds(getDoc(doc(hh1Db, 'meta/demo')));

    // Denied: other households and any centre data
    await assertFails(
      getDoc(doc(hh1Db, `households/${HOUSEHOLD_2}/whatsapp_thread/m2`)),
    );
    await assertFails(getDoc(doc(hh1Db, `centres/${CENTRE_FW}/tickets/t1`)));
  });

  it('denies all client writes (create, update, delete) for every role', async () => {
    const contexts = [
      testEnv.unauthenticatedContext().firestore(),
      testEnv
        .authenticatedContext('admin_fw', { role: 'centre_admin', centre_id: CENTRE_FW })
        .firestore(),
      testEnv
        .authenticatedContext('tech_1', {
          role: 'technician',
          centre_id: CENTRE_FW,
          technician_id: TECH_FW_1,
        })
        .firestore(),
      testEnv
        .authenticatedContext('hh_1', { household_id: HOUSEHOLD_1 })
        .firestore(),
      testEnv.authenticatedContext('platform_user', { role: 'platform' }).firestore(),
    ];

    for (const db of contexts) {
      await assertFails(
        setDoc(doc(db, `centres/${CENTRE_FW}/tickets/new_ticket`), { id: 'new' }),
      );
      await assertFails(
        updateDoc(doc(db, `centres/${CENTRE_FW}/tickets/t1`), { urgency_class: 'safety' }),
      );
      await assertFails(deleteDoc(doc(db, `centres/${CENTRE_FW}/tickets/t1`)));
      await assertFails(
        setDoc(doc(db, `centres/${CENTRE_FW}/visits/v1`), { status: 'done' }),
      );
      await assertFails(
        setDoc(doc(db, `households/${HOUSEHOLD_1}/whatsapp_thread/m_new`), { text: 'x' }),
      );
      await assertFails(setDoc(doc(db, 'meta/demo'), { active_case_id: 'C01' }));
    }
  });
});
