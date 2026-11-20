import 'dart:convert';
import 'dart:typed_data';

import 'package:kw_client/kw_client.dart';
import 'package:test/test.dart';

void main() {
  group('KwConfig', () {
    test('defaults point to local Part B mock servers', () {
      const cfg = KwConfig();
      expect(cfg.apiBaseUrl, 'http://localhost:8081/v1');
      expect(cfg.liveWsUrl, 'ws://localhost:8082/v1/live/call');
      expect(cfg.demoMode, isTrue);
      expect(cfg.isSandboxPayment, isTrue);
      expect(cfg.apiRootUri.toString(), 'http://localhost:8081/');
      expect(cfg.useFirestoreEmulator, isFalse);
    });

    test('builds emulator Firestore URL when host is configured', () {
      const cfg = KwConfig(
        firebaseProjectId: 'keepwell-local',
        firestoreEmulatorHost: '127.0.0.1:8080',
      );
      expect(cfg.useFirestoreEmulator, isTrue);
      expect(
        cfg.firestoreDocumentsBaseUrl,
        'http://127.0.0.1:8080/v1/projects/keepwell-local/databases/(default)/documents',
      );
    });
  });

  group('Core models JSON round-trip & unknown-field tolerance', () {
    test('TicketDetail full C03 round-trip ignores unknown fields', () {
      final raw = <String, dynamic>{
        'unknown_root_field': 'should_be_ignored',
        'card': {
          'id': 't-c03',
          'centre_id': 'c-fw',
          'trigger': 'household_call',
          'channel': 'voice',
          'job_type': 'repair',
          'status': 'assigned',
          'resolution': null,
          'urgency_class': 'standard',
          'needed_by': '2026-11-22T12:00:00+05:30',
          'safety_flag': false,
          'safety_reason': null,
          'entitlement': 'paid',
          'household': {
            'id': 'hh-1',
            'display_name': 'Sunita Sharma',
            'language': 'hi',
            'pincode': '500072',
            'locality': 'Kukatpally',
            'address_line': 'Flat 402, Kukatpally, Hyderabad',
            'verified_via': 'call_line',
            'linked_centres_count': 2,
            'extra_household_field': 123,
          },
          'appliance': {
            'id': 'app-1',
            'brand': 'Wavecrest',
            'category_code': 'washing_machine',
            'model_code': 'WC-FL70',
            'serial_masked': 'WCFL****981',
            'identity_status': 'verified',
            'purchase_date': '2024-10-30',
            'warranty_end': '2026-10-30',
            'future_field': true,
          },
          'complaint_summary': 'Washer not draining, showing E21',
          'language': 'hi',
          'created_at': '2026-11-21T07:12:00+05:30',
          'updated_at': '2026-11-21T08:12:00+05:30',
          'flags': ['stage_candidate', 'video_switched'],
        },
        'case_card': {
          'summary': 'Washer E21 drain timeout',
          'symptoms': ['Not draining', 'Error E21'],
          'error_codes': ['E21'],
          'what_was_tried': ['Drain filter cleaned on video'],
          'safety_notes': 'No electrical hazard',
          'identity_notes': 'Matched via call_line',
          'sources': [
            {
              'doc_title': 'wc_washer_manual.pdf',
              'page': 14,
              'uri': null,
              'snippet': 'E21 indicates drain timeout > 4 minutes',
            }
          ],
        },
        'urgency': [
          {
            'class': 'standard',
            'rule_codes': ['STD-DEFAULT'],
            'facts': {'unsafe_now': false},
            'assessed_by': 'agent',
            'reason': 'Wet floor only',
            'protective_steps_sent': false,
            'created_at': '2026-11-21T07:13:00+05:30',
          }
        ],
        'gates': [
          {
            'gate': 1,
            'asked_at': '2026-11-21T07:27:10+05:30',
            'answer': 'yes',
            'choice': null,
            'not_asked_reason': null,
          },
          {
            'gate': 2,
            'asked_at': '2026-11-21T07:27:35+05:30',
            'answer': 'yes',
            'choice': 'switch_to_video',
            'not_asked_reason': null,
          },
        ],
        'clarifying_qa': [
          {
            'seq': 1,
            'question': 'Any burning smell or electric shock?',
            'answer': 'No',
            'answer_source': 'voice',
            'asked_at': '2026-11-21T07:12:30+05:30',
          }
        ],
        'fix_attempts': [
          {
            'id': 'fix-1',
            'catalogue_code': 'SF-WM-DRAINFILTER-WC',
            'title': 'Clean drain pump filter',
            'offered_at': '2026-11-21T07:28:15+05:30',
            'steps_done': 6,
            'of': 6,
            'outcome': 'not_worked',
            'household_report': 'E21 returned',
            'observed_on_video': true,
          }
        ],
        'tried_summary': [
          {'code': 'SF-WM-DRAINFILTER-WC', 'outcome': 'not_worked'}
        ],
        'diagnosis': {
          'hypotheses': [
            {
              'fault_key': 'wm_drain_pump_jam',
              'label': 'Drain pump impeller jammed',
              'probability': 0.86,
              'evidence': ['E21 persisted after filter clean'],
              'citations': [
                {
                  'doc_title': 'wc_washer_manual.pdf',
                  'page': 14,
                  'uri': null,
                  'snippet': 'Replace WC-WM-DPUMP if jammed',
                }
              ],
            }
          ],
          'abstained': false,
          'reason': null,
          'rerun_of': 'diag-v1',
          'model_version': 'gemini-3.8-flash',
        },
        'visit_plan': {
          'id': 'vp-1',
          'version': 2,
          'trigger_reason': 'safe_fix_not_worked',
          'already_tried': ['Clean drain pump filter'],
          'required_skills': ['washing_machine'],
          'est_duration_p50_min': 40,
          'est_duration_p80_min': 65,
          'tools_needed': ['Multimeter'],
          'requires_safety_cert': [],
          'parts': [
            {
              'part_no': 'WC-WM-DPUMP',
              'name': 'Drain pump',
              'probability': 0.82,
              'quantity': 1,
              'source_ladder': 'centre',
              'ready': true,
            }
          ],
          'access_notes': 'Gate security requires visitor entry',
          'confidence': 0.86,
        },
        'candidates': [
          {
            'technician_id': 'tech-1',
            'name': 'Ramesh Kumar',
            'rank': 1,
            'score': 89.5,
            'score_breakdown': {
              'fix_confidence': 27.5,
              'parts_readiness': 23.0,
              'time_to_visit': 17.5,
              'route_cost': 12.5,
              'reliability': 4.5,
              'household_fit': 4.5,
            },
            'slot_start': '2026-11-21T14:00:00+05:30',
            'slot_end': '2026-11-21T16:00:00+05:30',
            'outcome': 'chosen',
            'chosen_by': 'agent',
            'override_reason': null,
            'why': 'Highest fix confidence',
          }
        ],
        'slot_proposals': [
          {
            'slot_start': '2026-11-21T14:00:00+05:30',
            'slot_end': '2026-11-21T16:00:00+05:30',
            'price_low_paise': 100000,
            'price_high_paise': 223500,
            'shown_at': '2026-11-21T08:12:00+05:30',
            'accepted': true,
          }
        ],
        'quotes': [
          {
            'id': 'q-1',
            'version': 1,
            'quote_type': 'firm',
            'lines': [
              {
                'kind': 'part',
                'description': 'Drain pump (WC-WM-DPUMP)',
                'amount_paise': 123500,
                'payer': 'household',
              }
            ],
            'total_paise': 223500,
            'household_paise': 223500,
            'covered_paise': 0,
            'approved_at': '2026-11-21T08:15:00+05:30',
            'approval_method': 'magic_link',
          }
        ],
        'payments': [
          {
            'id': 'pay-1',
            'quote_id': 'q-1',
            'amount_paise': 223500,
            'status': 'pending',
            'method': 'google_pay',
            'upi_intent_url': null,
            'google_pay': {
              'environment': 'TEST',
              'merchant_name': 'Frost and Wave Service Point',
              'merchant_id': 'BCR2DN4TKEEPWELL',
              'gateway': 'example',
              'gateway_merchant_id': 'exampleGatewayMerchantId',
              'transaction_info': {
                'currency_code': 'INR',
                'total_price_status': 'FINAL',
                'total_price': '2235.00',
              },
            },
            'payment_ref': null,
            'created_at': '2026-11-21T08:16:00+05:30',
            'expires_at': '2026-11-21T08:46:00+05:30',
            'paid_at': null,
          }
        ],
        'debrief': {
          'id': 'deb-1',
          'visit_id': 'v-1',
          'status': 'ready',
          'language': 'hi',
          'transcript': 'Replaced drain pump and rubber ring',
          'extracted': {
            'fault_found': 'Impeller jammed',
            'work_done': 'Replaced WC-WM-DPUMP',
            'parts_used': [
              {'part_no': 'WC-WM-DPUMP', 'quantity': 1}
            ],
            'advice_for_household': 'Clean filter quarterly',
            'appliance_notes': 'No leaks',
            'follow_up_needed': false,
          },
          'unresolved': ['rubber ring (unmatched — needs checking)'],
          'confirmed_at': null,
        },
        'visit': {
          'id': 'v-1',
          'technician_id': 'tech-1',
          'planned_start': '2026-11-21T14:00:00+05:30',
          'planned_end': '2026-11-21T16:00:00+05:30',
          'check_in_at': null,
          'check_out_at': null,
          'outcome': null,
          'closure_confirmed_at': null,
          'rating': null,
        },
        'timeline': [
          {
            'at': '2026-11-21T07:12:00+05:30',
            'type': 'conversation_started',
            'actor': 'household',
            'title': 'C03 received via voice',
            'detail': 'Washer E21',
            'ref': 't-c03',
          }
        ],
        'authority': {
          'level': 'authorised_service',
          'decision': 'proceed',
        },
      };

      final parsed = TicketDetail.fromJson(raw);
      final roundTrip = TicketDetail.fromJson(parsed.toJson());

      expect(roundTrip.card.id, 't-c03');
      expect(roundTrip.card.household.displayName, 'Sunita Sharma');
      expect(roundTrip.card.appliance?.brand, 'Wavecrest');
      expect(roundTrip.gates.length, 2);
      expect(roundTrip.gates[1].choice, 'switch_to_video');
      expect(roundTrip.fixAttempts.first.ofSteps, 6);
      expect(roundTrip.diagnosis?.hypotheses.first.probability, 0.86);
      expect(roundTrip.visitPlan?.parts.first.partNo, 'WC-WM-DPUMP');
      expect(roundTrip.candidates.first.scoreBreakdown.fixConfidence, 27.5);
      expect(
        roundTrip.payments.first.googlePay?.transactionInfo.totalPrice,
        '2235.00',
      );
      expect(roundTrip.debrief?.unresolved.length, 1);
      expect(roundTrip.authority.level, 'authorised_service');
    });

    test('DemoCase, DemoHousehold, CentreOverview, TechnicianSummary, SafeFixEntry, WhatsAppMessage, ConversationTurn, PagedList', () {
      final demoCase = DemoCase.fromJson({
        'case_id': 'C03',
        'ticket_id': 't-c03',
        'trigger': 'household_call',
        'channel': 'voice',
        'centre_key': 'c_fw',
        'centre_id': 'c-fw',
        'centre_name': 'Frost and Wave Service Point',
        'urgency_class': 'standard',
        'safety_flag': false,
        'stage_candidate': true,
        'summary': 'Hindi washer E21',
        'unexpected_key': 'ignored',
      });
      expect(DemoCase.fromJson(demoCase.toJson()).stageCandidate, isTrue);

      final hh = DemoHousehold.fromJson({
        'household_id': 'hh-1',
        'display_name': 'Sunita Sharma',
        'phone_masked': '+91 ••••• ••577',
        'language': 'hi',
        'magic_token': 'kwm_1234',
        'centre_key': 'c_fw',
        'centre_id': 'c-fw',
      });
      expect(DemoHousehold.fromJson(hh.toJson()).magicToken, 'kwm_1234');

      final overview = CentreOverview.fromJson({
        'centre_id': 'c-fw',
        'centre_key': 'c_fw',
        'centre_name': 'Frost and Wave Service Point',
        'open_by_class': {'safety': 1, 'urgent': 2, 'standard': 5, 'planned': 1},
        'first_time_fix': 0.86,
        'fvr_14d': 0.82,
        'self_fix_resolution': 0.24,
        'gate_funnel': {
          'gate1_asked': 20,
          'gate1_yes': 14,
          'gate2_asked': 14,
          'switch_to_video': 7,
        },
        'urgency_agreement': 0.92,
        'override_rate': 6.4,
        'parts_ready_at_visit': 0.87,
        'jobs_per_tech_day': 3.2,
      });
      expect(CentreOverview.fromJson(overview.toJson()).fvr14d, 0.82);

      final tech = TechnicianSummary.fromJson({
        'id': 'tech-1',
        'centre_id': 'c-fw',
        'centre_key': 'c_fw',
        'name': 'Ramesh Kumar',
        'languages': ['hi', 'te', 'en'],
        'shift_start': '09:00',
        'shift_end': '18:00',
        'vehicle_type': 'two_wheeler',
        'safety_certs': ['electrical'],
        'active': true,
        'status': 'available',
        'last_location': {'lat': 17.49, 'lon': 78.39},
        'last_ping_at': '2026-11-21T08:15:00+05:30',
        'skills': [
          {'brand': 'Wavecrest', 'category_code': 'washing_machine', 'level': 3}
        ],
        'metrics': {'first_time_fix_rate': 0.89},
      });
      expect(TechnicianSummary.fromJson(tech.toJson()).lastLocation?['lat'], 17.49);

      final sf = SafeFixEntry.fromJson({
        'id': 'sf-1',
        'code': 'SF-WM-DRAINFILTER-WC',
        'category_code': 'washing_machine',
        'brand': 'Wavecrest',
        'fault_family': 'drainage',
        'title': 'Clean drain filter',
        'symptom_terms': ['E21', 'not draining'],
        'steps': ['Turn off machine', 'Open flap'],
        'step_count': 2,
        'est_minutes': 10,
        'reversible': true,
        'needs_tools': false,
        'opens_panel': false,
        'worst_case': 'Minor water spill',
        'reviewer_name': 'Lead Eng',
        'status': 'active',
        'effectiveness': {'resolution_rate': 0.45},
      });
      expect(SafeFixEntry.fromJson(sf.toJson()).code, 'SF-WM-DRAINFILTER-WC');

      final wa = WhatsAppMessage.fromJson({
        'id': 'wa-1',
        'direction': 'out',
        'type': 'text',
        'text': 'Are you okay to try a quick, safe fix yourself first?',
        'media_url': null,
        'template': 'gate_1',
        'at': '2026-11-21T08:00:00+05:30',
        'ticket_id': 't-c03',
        'status': 'read',
      });
      expect(WhatsAppMessage.fromJson(wa.toJson()).template, 'gate_1');

      final turn = ConversationTurn.fromJson({
        'id': 'turn-1',
        'at': '2026-11-21T08:01:00+05:30',
        'speaker': 'household',
        'text': 'E21 आ रहा है',
        'lang': 'hi',
        'final': true,
        'kind': 'speech',
      });
      expect(ConversationTurn.fromJson(turn.toJson()).isFinal, isTrue);

      final paged = PagedList.fromJson(
        {
          'items': [demoCase.toJson()],
          'next_cursor': '50',
        },
        DemoCase.fromJson,
      );
      expect(paged.items.length, 1);
      expect(paged.hasMore, isTrue);
    });
  });

  group('KwApiError & KwApiException', () {
    test('parses Contract §5 error envelope', () {
      final err = KwApiError.fromJson({
        'error': {
          'code': 'invalid_urgency_class',
          'message': 'Invalid class: emergency',
          'field': 'class',
          'request_id': 'req_abc123',
        },
      });
      expect(err.code, 'invalid_urgency_class');
      expect(err.message, 'Invalid class: emergency');
      expect(err.field, 'class');
      expect(err.requestId, 'req_abc123');

      final ex = KwApiException(statusCode: 429, error: err, retryAfterSeconds: 5);
      expect(ex.isRateLimited, isTrue);
      expect(ex.isTransient, isTrue);
    });
  });

  group('LiveServerMessage parsing (Contract §7)', () {
    test('parses every Contract §7 message frame and binary PCM16', () {
      final ready = LiveServerMessage.fromWire(jsonEncode({
        'type': 'ready',
        'conversation_id': 'conv-1',
        'session_id': 'sess-1',
        'centre_name': 'Frost and Wave Service Point',
        'recording_notice': 'This call may be recorded.',
      }));
      expect(ready, isA<LiveReadyMessage>());
      expect((ready as LiveReadyMessage).conversationId, 'conv-1');

      final transcript = LiveServerMessage.fromWire(jsonEncode({
        'type': 'transcript',
        'speaker': 'agent',
        'text': 'Namaste',
        'final': true,
        'lang': 'hi',
      }));
      expect(transcript, isA<LiveTranscriptMessage>());
      expect((transcript as LiveTranscriptMessage).isFinal, isTrue);

      final videoLink = LiveServerMessage.fromWire(jsonEncode({
        'type': 'video_link',
        'url': 'https://keepwell.app/v/kwm_123',
        'expires_at': '2026-11-21T09:00:00+05:30',
      }));
      expect(videoLink, isA<LiveVideoLinkMessage>());

      final modality = LiveServerMessage.fromWire(jsonEncode({
        'type': 'modality',
        'value': 'video',
      }));
      expect((modality as LiveModalityMessage).value, 'video');

      final hint = LiveServerMessage.fromWire(jsonEncode({
        'type': 'ui_hint',
        'kind': 'show_drain_filter',
        'text': 'Point at the drain filter.',
      }));
      expect((hint as LiveUiHintMessage).kind, 'show_drain_filter');

      final event = LiveServerMessage.fromWire(jsonEncode({
        'type': 'event',
        'id': 'ev-1',
        'at': '2026-11-21T08:00:00+05:30',
        'centre_id': 'c-fw',
        'ticket_id': 't-c03',
        'conversation_id': 'conv-1',
        'event_type': 'gate_asked',
        'actor': 'agent',
        'title': 'Consent Gate 1 asked',
        'detail': 'Safe fix',
        'payload': {'gate': 1},
      }));
      expect(event, isA<LiveEventMessage>());
      expect((event as LiveEventMessage).event.type, 'gate_asked');

      final goAway = LiveServerMessage.fromWire(jsonEncode({
        'type': 'go_away',
        'seconds': 30,
      }));
      expect((goAway as LiveGoAwayMessage).seconds, 30);

      final ended = LiveServerMessage.fromWire(jsonEncode({
        'type': 'ended',
        'reason': 'completed',
        'ticket_id': 't-c03',
      }));
      expect((ended as LiveEndedMessage).reason, 'completed');

      final err = LiveServerMessage.fromWire(jsonEncode({
        'type': 'error',
        'code': 'invalid_start',
        'message': 'Bad frame',
      }));
      expect((err as LiveErrorMessage).code, 'invalid_start');

      final audio = LiveServerMessage.fromWire(Uint8List.fromList([0, 1, 2, 3]));
      expect(audio, isA<LiveAudioChunkMessage>());
      expect((audio as LiveAudioChunkMessage).pcm16Bytes.length, 4);

      final unknown = LiveServerMessage.fromWire(jsonEncode({
        'type': 'future_event_type',
        'foo': 'bar',
      }));
      expect(unknown, isA<LiveUnknownMessage>());
    });
  });

  group('KwAuthHelper & KwFirestoreClient', () {
    test('provides demo personas for all 9 centres plus parts, brand, platform', () {
      expect(KwAuthHelper.demoCentres.length, 9);
      final consoleFw = KwAuthHelper.findPersonaByEmail('console.c_fw@keepwell.demo');
      expect(consoleFw?.role, KwRole.centreAdmin);
      expect(consoleFw?.centreKey, 'c_fw');

      final tech1 = KwAuthHelper.findPersonaByEmail('tech1.c_av@keepwell.demo');
      expect(tech1?.role, KwRole.technician);

      final parts = KwAuthHelper.findPersonaByEmail('parts.demo@keepwell.demo');
      expect(parts?.role, KwRole.partsCentre);

      final brand = KwAuthHelper.findPersonaByEmail('brand.wavecrest@keepwell.demo');
      expect(brand?.role, KwRole.brand);

      final platform = KwAuthHelper.findPersonaByEmail('platform@keepwell.demo');
      expect(platform?.role, KwRole.platform);
    });

    test('decodes Firestore REST document values cleanly', () {
      final decoded = KwFirestoreClient.decodeDocument({
        'name': 'projects/keepwell-demo/databases/(default)/documents/centres/c_fw/feed/ev-99',
        'fields': {
          'type': {'stringValue': 'gate_asked'},
          'at': {'timestampValue': '2026-11-21T08:00:00Z'},
          'centre_id': {'stringValue': 'c_fw'},
          'actor': {'stringValue': 'agent'},
          'title': {'stringValue': 'Gate 1 asked'},
          'detail': {'stringValue': 'Safe fix'},
          'payload': {
            'mapValue': {
              'fields': {
                'gate': {'integerValue': '1'},
                'ok': {'booleanValue': true},
                'tags': {
                  'arrayValue': {
                    'values': [
                      {'stringValue': 'hi'},
                    ],
                  },
                },
              },
            },
          },
        },
      });

      final ev = LiveEvent.fromJson(decoded);
      expect(ev.id, 'ev-99');
      expect(ev.type, 'gate_asked');
      expect(ev.payload['gate'], 1);
      expect(ev.payload['ok'], isTrue);
      expect(ev.payload['tags'], ['hi']);
    });
  });
}
